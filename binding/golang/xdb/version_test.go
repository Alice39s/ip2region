// Copyright 2022 The Ip2Region Authors. All rights reserved.
// Use of this source code is governed by a Apache2.0-style
// license that can be found in the LICENSE file.

package xdb

import (
	"testing"
)

func TestVersionFromHeader(t *testing.T) {
	cases := []struct {
		version    uint16
		ipVersion  uint16
		expectErr  bool
		expectName string
		noEndIp    bool
	}{
		{Structure20, IPv4VersionNo, false, "IPv4", false},
		{Structure30, IPv4VersionNo, false, "IPv4", false},
		{Structure30, IPv6VersionNo, false, "IPv6", false},
		{Structure40, IPv4VersionNo, false, "IPv4", true},
		{Structure40, IPv6VersionNo, false, "IPv6", true},
		{5, IPv4VersionNo, true, "", false},
		{Structure40, 5, true, "", false},
	}

	for _, c := range cases {
		h := &Header{
			Version:   c.version,
			IPVersion: int(c.ipVersion),
		}
		v, err := VersionFromHeader(h)
		if c.expectErr {
			if err == nil {
				t.Fatalf("version=%d ipVersion=%d expected error, got nil", c.version, c.ipVersion)
			}
			continue
		}
		if err != nil {
			t.Fatalf("version=%d ipVersion=%d unexpected error: %s", c.version, c.ipVersion, err)
		}
		if v.Name != c.expectName {
			t.Fatalf("version=%d ipVersion=%d expected %s, got %s", c.version, c.ipVersion, c.expectName, v.Name)
		}
		if v.NoEndIp != c.noEndIp {
			t.Fatalf("version=%d ipVersion=%d expected NoEndIp=%v, got %v", c.version, c.ipVersion, c.noEndIp, v.NoEndIp)
		}
		if c.ipVersion == IPv4VersionNo && !v.NoEndIp && v.SegmentIndexSize != 14 {
			t.Fatalf("IPv4 classic segment index size should be 14, got %d", v.SegmentIndexSize)
		}
		if c.ipVersion == IPv4VersionNo && v.NoEndIp && v.SegmentIndexSize != 10 {
			t.Fatalf("IPv4 no-end-ip segment index size should be 10, got %d", v.SegmentIndexSize)
		}
		if c.ipVersion == IPv6VersionNo && !v.NoEndIp && v.SegmentIndexSize != 38 {
			t.Fatalf("IPv6 classic segment index size should be 38, got %d", v.SegmentIndexSize)
		}
		if c.ipVersion == IPv6VersionNo && v.NoEndIp && v.SegmentIndexSize != 22 {
			t.Fatalf("IPv6 no-end-ip segment index size should be 22, got %d", v.SegmentIndexSize)
		}
	}
}
