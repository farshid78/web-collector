package parser

import "strings"

type ConfigGroups struct {
    VMess  []string
    VLess  []string
    Trojan []string
    SS     []string
}

func SplitConfigs(list []string) ConfigGroups {
    var g ConfigGroups

    for _, c := range list {
        c = strings.TrimSpace(c)

        switch {
        case strings.HasPrefix(c, "vmess://"):
            g.VMess = append(g.VMess, c)
        case strings.HasPrefix(c, "vless://"):
            g.VLess = append(g.VLess, c)
        case strings.HasPrefix(c, "trojan://"):
            g.Trojan = append(g.Trojan, c)
        case strings.HasPrefix(c, "ss://"):
            g.SS = append(g.SS, c)
        }
    }

    return g
}
