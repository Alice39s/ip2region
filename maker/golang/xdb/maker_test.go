// Copyright 2022 The Ip2Region Authors. All rights reserved.
// Use of this source code is governed by a Apache2.0-style
// license that can be found in the LICENSE file.

package xdb

import (
	"encoding/binary"
	"os"
	"strings"
	"testing"
)

// createTestSourceFile writes a temporary source text file and returns its path.
func createTestSourceFile(t *testing.T, content string) string {
	t.Helper()
	f, err := os.CreateTemp("", "ip2region-source-*.txt")
	if err != nil {
		t.Fatalf("create temp source file: %s", err)
	}
	defer f.Close()

	if _, err := f.WriteString(content); err != nil {
		t.Fatalf("write source file: %s", err)
	}
	return f.Name()
}

// makeTestXdb generates a temporary xdb file from the given source content.
func makeTestXdb(t *testing.T, version *Version, srcContent string) string {
	t.Helper()
	srcFile := createTestSourceFile(t, srcContent)
	dstFile := tempFileName(t, "*.xdb")

	maker, err := NewMaker(version, VectorIndexPolicy, srcFile, dstFile, nil)
	if err != nil {
		t.Fatalf("new maker: %s", err)
	}

	if err := maker.Init(); err != nil {
		t.Fatalf("maker init: %s", err)
	}
	if err := maker.Start(); err != nil {
		t.Fatalf("maker start: %s", err)
	}
	if err := maker.End(); err != nil {
		t.Fatalf("maker end: %s", err)
	}

	return dstFile
}

func tempFileName(t *testing.T, pattern string) string {
	t.Helper()
	f, err := os.CreateTemp("", pattern)
	if err != nil {
		t.Fatalf("create temp file: %s", err)
	}
	name := f.Name()
	f.Close()
	return name
}

// TestMaker_NoEndIpFormat verifies the generated xdb uses structure 4.0 and the
// segment index block no longer contains end_ip.
func TestMaker_NoEndIpFormat(t *testing.T) {
	src := "1.1.1.0|1.1.1.255|TestRegion"
	dbFile := makeTestXdb(t, IPv4, src)

	f, err := os.Open(dbFile)
	if err != nil {
		t.Fatalf("open xdb: %s", err)
	}
	defer f.Close()

	header, err := LoadXdbHeader(f)
	if err != nil {
		t.Fatalf("load header: %s", err)
	}

	version := binary.LittleEndian.Uint16(header)
	if version != VersionNo {
		t.Fatalf("expected header version %d, got %d", VersionNo, version)
	}

	ipVersion := binary.LittleEndian.Uint16(header[16:])
	if int(ipVersion) != IPv4.Id {
		t.Fatalf("expected ip version %d, got %d", IPv4.Id, ipVersion)
	}

	startPtr := binary.LittleEndian.Uint32(header[8:])
	endPtr := binary.LittleEndian.Uint32(header[12:])
	indexSize := int(endPtr - startPtr)
	if indexSize%IPv4.SegmentIndexSize != 0 {
		t.Fatalf("segment index size %d is not a multiple of %d", indexSize, IPv4.SegmentIndexSize)
	}

	searcher, err := NewSearcher(IPv4, dbFile)
	if err != nil {
		t.Fatalf("new searcher: %s", err)
	}
	defer searcher.Close()

	region, _, err := searcher.Search([]byte{1, 1, 1, 100})
	if err != nil {
		t.Fatalf("search: %s", err)
	}
	if !strings.HasPrefix(region, "TestRegion") {
		t.Fatalf("expected region to start with TestRegion, got `%s`", region)
	}
}

// TestMaker_ContinuousFill verifies that the maker automatically fills the gaps
// between user segments with EmptyRegion, which is required by the no-end_ip format.
func TestMaker_ContinuousFill(t *testing.T) {
	src := "1.1.1.10|1.1.1.20|A\n" +
		"1.1.1.30|1.1.1.40|B\n"
	dbFile := makeTestXdb(t, IPv4, src)

	searcher, err := NewSearcher(IPv4, dbFile)
	if err != nil {
		t.Fatalf("new searcher: %s", err)
	}
	defer searcher.Close()

	cases := []struct {
		ip     []byte
		want   string
		reason string
	}{
		{[]byte{1, 1, 1, 10}, "A", "segment A start boundary"},
		{[]byte{1, 1, 1, 15}, "A", "segment A middle"},
		{[]byte{1, 1, 1, 20}, "A", "segment A end boundary"},
		{[]byte{1, 1, 1, 21}, "", "gap between A and B should be EmptyRegion"},
		{[]byte{1, 1, 1, 25}, "", "gap between A and B should be EmptyRegion"},
		{[]byte{1, 1, 1, 29}, "", "gap between A and B should be EmptyRegion"},
		{[]byte{1, 1, 1, 30}, "B", "segment B start boundary"},
		{[]byte{1, 1, 1, 35}, "B", "segment B middle"},
		{[]byte{1, 1, 1, 40}, "B", "segment B end boundary"},
		{[]byte{1, 1, 1, 0}, "", "before segment A should be EmptyRegion"},
		{[]byte{1, 1, 1, 41}, "", "after segment B should be EmptyRegion"},
		{[]byte{2, 0, 0, 0}, "", "outside the only filled prefix should be EmptyRegion"},
	}

	for _, c := range cases {
		got, _, err := searcher.Search(c.ip)
		if err != nil {
			t.Fatalf("search %s: %s", IP2String(c.ip), err)
		}
		if got != c.want {
			t.Fatalf("%s: expected `%s`, got `%s`", c.reason, c.want, got)
		}
	}
}

// TestMaker_BoundaryIPs verifies the minimum and maximum IPs of the whole IP
// space are searchable and return EmptyRegion when not covered by user data.
func TestMaker_BoundaryIPs(t *testing.T) {
	src := "128.0.0.0|128.0.0.255|Center\n"
	dbFile := makeTestXdb(t, IPv4, src)

	searcher, err := NewSearcher(IPv4, dbFile)
	if err != nil {
		t.Fatalf("new searcher: %s", err)
	}
	defer searcher.Close()

	cases := []struct {
		ip   string
		want string
	}{
		{"0.0.0.0", ""},
		{"127.255.255.255", ""},
		{"128.0.0.0", "Center"},
		{"128.0.0.255", "Center"},
		{"129.0.0.0", ""},
		{"255.255.255.255", ""},
	}

	for _, c := range cases {
		ip, err := ParseIP(c.ip)
		if err != nil {
			t.Fatalf("parse ip %s: %s", c.ip, err)
		}
		got, _, err := searcher.Search(ip)
		if err != nil {
			t.Fatalf("search %s: %s", c.ip, err)
		}
		if got != c.want {
			t.Fatalf("search %s: expected `%s`, got `%s`", c.ip, c.want, got)
		}
	}
}

// TestMaker_IPv6ContinuousFill verifies IPv6 gap filling and boundary handling.
func TestMaker_IPv6ContinuousFill(t *testing.T) {
	src := "2001:db8::|2001:db8::ff|V6A\n" +
		"2001:db8::200|2001:db8::2ff|V6B\n"
	dbFile := makeTestXdb(t, IPv6, src)

	searcher, err := NewSearcher(IPv6, dbFile)
	if err != nil {
		t.Fatalf("new searcher: %s", err)
	}
	defer searcher.Close()

	cases := []struct {
		ip   string
		want string
	}{
		{"2001:db8::", "V6A"},
		{"2001:db8::ff", "V6A"},
		{"2001:db8::100", ""}, // gap: 0x100 - 0x1ff
		{"2001:db8::1ff", ""},
		{"2001:db8::200", "V6B"},
		{"2001:db8::2ff", "V6B"},
		{"2001:db8::300", ""},
		{"::", ""},
		{"ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff", ""},
	}

	for _, c := range cases {
		ip, err := ParseIP(c.ip)
		if err != nil {
			t.Fatalf("parse ip %s: %s", c.ip, err)
		}
		got, _, err := searcher.Search(ip)
		if err != nil {
			t.Fatalf("search %s: %s", c.ip, err)
		}
		if got != c.want {
			t.Fatalf("search %s: expected `%s`, got `%s`", c.ip, c.want, got)
		}
	}
}
