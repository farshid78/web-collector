package main

import (
    "fmt"
    "regexp"
    "web-collector/telegram"
    "web-collector/storage"
)

func main() {
    fmt.Println("شروع جمع‌آوری کانفیگ‌های V2Ray...")

    channels := []string{
        "V2rayNG_VPN",
        "ShadowProxy66",
        "VmessFree",
        "ConfigsHUB2",
    }

    var all []string

    pattern := regexp.MustCompile(`(vmess|vless|trojan|ss)://[^\s]+`)

    for _, ch := range channels {
        fmt.Println("در حال دریافت پیام‌ها از کانال:", ch)

        msgs, err := telegram.GetChannelMessages(BOT_TOKEN, ch)
        if err != nil {
            fmt.Println("خطا:", err)
            continue
        }

        for _, m := range msgs {
            found := pattern.FindAllString(m, -1)
            all = append(all, found...)
        }
    }

    fmt.Println("تعداد کانفیگ‌های پیدا شده:", len(all))

    storage.SaveToFile("results.txt", all)

    fmt.Println("فایل results.txt ساخته شد.")
}
