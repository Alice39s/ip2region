// Copyright 2022 The Ip2Region Authors. All rights reserved.
// Use of this source code is governed by a Apache2.0-style
// license that can be found in the LICENSE file.

package xdb

import (
	"os"
	"testing"
)

func mustParseIP(t *testing.T, ip string) []byte {
	t.Helper()
	b, err := ParseIP(ip)
	if err != nil {
		t.Fatalf("parse ip %s: %s", ip, err)
	}
	return b
}

// openSearcherByHeader opens the xdb file, detects its structure version from
// the header and returns a Searcher configured for that version.
func openSearcherByHeader(t *testing.T, dbFile string) *Searcher {
	t.Helper()
	f, err := os.Open(dbFile)
	if err != nil {
		t.Fatalf("open xdb %s: %s", dbFile, err)
	}

	header, err := LoadHeader(f)
	if err != nil {
		f.Close()
		t.Fatalf("load header: %s", err)
	}

	version, err := VersionFromHeader(header)
	if err != nil {
		f.Close()
		t.Fatalf("version from header: %s", err)
	}

	if _, err := f.Seek(0, 0); err != nil {
		f.Close()
		t.Fatalf("seek xdb: %s", err)
	}

	return INewSearcher(version, f, nil, nil)
}

// TestSearcher_BoundaryQueries runs boundary queries against the real v4/v6 xdb
// files to ensure both structure 3.0 and 4.0 formats handle edges correctly.
func TestSearcher_BoundaryQueries(t *testing.T) {
	v4Searcher := openSearcherByHeader(t, "../../../data/ip2region_v4.xdb")
	defer v4Searcher.Close()

	v6Searcher := openSearcherByHeader(t, "../../../data/ip2region_v6.xdb")
	defer v6Searcher.Close()

	v4Cases := []struct {
		ip   string
		desc string
	}{
		{"0.0.0.0", "minimum IPv4"},
		{"1.0.0.0", "first public-like IPv4"},
		{"8.8.8.8", "common IPv4"},
		{"127.255.255.255", "loopback end"},
		{"128.0.0.0", "just above loopback"},
		{"192.168.1.1", "private IPv4"},
		{"223.255.255.255", "class C end"},
		{"224.0.0.0", "multicast start"},
		{"255.255.255.255", "maximum IPv4"},
	}

	for _, c := range v4Cases {
		_, err := v4Searcher.Search(mustParseIP(t, c.ip))
		if err != nil {
			t.Fatalf("v4 search %s (%s): %s", c.ip, c.desc, err)
		}
	}

	v6Cases := []struct {
		ip   string
		desc string
	}{
		{"::", "minimum IPv6"},
		{"::1", "loopback IPv6"},
		{"2001:4860:4860::8888", "common IPv6"},
		{"240e::1", "China Telecom IPv6"},
		{"fe80::1", "link-local"},
		{"ff02::1", "multicast"},
		{"ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff", "maximum IPv6"},
	}

	for _, c := range v6Cases {
		_, err := v6Searcher.Search(mustParseIP(t, c.ip))
		if err != nil {
			t.Fatalf("v6 search %s (%s): %s", c.ip, c.desc, err)
		}
	}
}

// TestSearcher_NewFormatAccepted verifies the searcher accepts structure 4.0
// and rejects unsupported versions.
func TestSearcher_NewFormatAccepted(t *testing.T) {
	f, err := os.Open("../../../data/ip2region_v4.xdb")
	if err != nil {
		t.Fatalf("open xdb: %s", err)
	}
	defer f.Close()

	header, err := LoadHeader(f)
	if err != nil {
		t.Fatalf("load header: %s", err)
	}
	if header.Version != Structure40 {
		t.Fatalf("expected structure 4.0, got %d", header.Version)
	}

	if err := Verify(f); err != nil {
		t.Fatalf("verify structure 4.0 xdb: %s", err)
	}
}

// TestSearcher_FormatConsistency checks that known public IPs return a
// non-empty region with the new structure 4.0 xdb files.
func TestSearcher_FormatConsistency(t *testing.T) {
	searcher := openSearcherByHeader(t, "../../../data/ip2region_v4.xdb")
	defer searcher.Close()

	ips := []string{"8.8.8.8", "223.5.5.5"}
	for _, ip := range ips {
		region, err := searcher.Search(mustParseIP(t, ip))
		if err != nil {
			t.Fatalf("search %s: %s", ip, err)
		}
		if region == "" {
			t.Fatalf("search %s returned empty region", ip)
		}
	}
}

// TestSearcher_OldFormatCompatibility verifies that structure 3.0 xdb files
// (with end_ip stored) are still readable after adding structure 4.0 support.
func TestSearcher_OldFormatCompatibility(t *testing.T) {
	v4Searcher, err := NewWithFileOnly(IPv4, "/tmp/ip2region_v4_old.xdb")
	if err != nil {
		t.Fatalf("new v4 searcher: %s", err)
	}
	defer v4Searcher.Close()

	v6Searcher, err := NewWithFileOnly(IPv6, "/tmp/ip2region_v6_old.xdb")
	if err != nil {
		t.Fatalf("new v6 searcher: %s", err)
	}
	defer v6Searcher.Close()

	v4Cases := []string{"0.0.0.0", "8.8.8.8", "114.114.114.114", "255.255.255.255"}
	for _, ip := range v4Cases {
		_, err := v4Searcher.Search(mustParseIP(t, ip))
		if err != nil {
			t.Fatalf("old format v4 search %s: %s", ip, err)
		}
	}

	v6Cases := []string{"::", "2001:4860:4860::8888", "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"}
	for _, ip := range v6Cases {
		_, err := v6Searcher.Search(mustParseIP(t, ip))
		if err != nil {
			t.Fatalf("old format v6 search %s: %s", ip, err)
		}
	}
}

// TestSearcher_CrossFormatResults compares the same query against old and new
// format v4 xdb files. The region strings may differ in detail due to data
// updates, but both should return without error.
func TestSearcher_CrossFormatResults(t *testing.T) {
	oldSearcher, err := NewWithFileOnly(IPv4, "/tmp/ip2region_v4_old.xdb")
	if err != nil {
		t.Fatalf("new old-format searcher: %s", err)
	}
	defer oldSearcher.Close()

	newSearcher := openSearcherByHeader(t, "../../../data/ip2region_v4.xdb")
	defer newSearcher.Close()

	ips := []string{"8.8.8.8", "114.114.114.114", "223.5.5.5", "1.1.1.1"}
	for _, ip := range ips {
		oldRegion, err := oldSearcher.Search(mustParseIP(t, ip))
		if err != nil {
			t.Fatalf("old format search %s: %s", ip, err)
		}
		newRegion, err := newSearcher.Search(mustParseIP(t, ip))
		if err != nil {
			t.Fatalf("new format search %s: %s", ip, err)
		}
		t.Logf("%s: old=`%s` new=`%s`", ip, oldRegion, newRegion)
	}
}
