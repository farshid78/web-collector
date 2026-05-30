package main

import (
    "fmt"
    "strings"

    "github.com/PuerkitoBio/goquery"
    "web-collector/input"
    "web-collector/parser"
    "web-collector/scraper"
    "web-collector/storage"
)

func main() {
    fmt.Println("شروع برنامه جمع‌آوری کانفیگ‌های V2Ray...\n")

    sources, err := input.ReadSourcesFromCSV("sources.csv")
    if err != nil {
        fmt.Println("خطا در خواندن فایل CSV:", err)
        return
    }

    fmt.Printf("تعداد منابع: %d\n\n", len(sources))

    var allConfigs []string
    pattern := `(vmess|vless|trojan|ss)://[^\s]+`

    for _, src := range sources {
        fmt.Println("در حال اسکرپ:", src.URL)

        doc, err := scraper.FetchDocument(src.URL)
        if err != nil {
            fmt.Println("   خطا در دریافت صفحه:", err)
            continue
        }

        text := extractText(doc)
        matches := parser.ExtractByPattern(text, pattern)

        if len(matches) == 0 {
            fmt.Println("   هیچ کانفیگی پیدا نشد.")
            continue
        }

        fmt.Printf("   کانفیگ‌های پیدا شده: %d\n", len(matches))
        allConfigs = append(allConfigs, matches...)
    }

    cleaned := uniqueAndClean(allConfigs)
    fmt.Printf("\nتعداد نهایی کانفیگ‌های یکتا: %d\n", len(cleaned))

    // دسته‌بندی
    groups := parser.SplitConfigs(cleaned)

    // ذخیرهٔ فایل‌های جداگانه
    storage.SaveMultiple(map[string][]string{
        "vmess":  groups.VMess,
        "vless":  groups.VLess,
        "trojan": groups.Trojan,
        "ss":     groups.SS,
    })

    // ساخت subscription نهایی
    storage.SaveSubscription("subscription.txt", cleaned)

    fmt.Println("\nفایل‌های خروجی ساخته شدند:")
    fmt.Println("- results.txt (همه کانفیگ‌ها)")
    fmt.Println("- vmess.txt")
    fmt.Println("- vless.txt")
    fmt.Println("- trojan.txt")
    fmt.Println("- ss.txt")
    fmt.Println("- subscription.txt (فایل نهایی)")
}

func extractText(doc *goquery.Document) string {
    return doc.Text()
}

func uniqueAndClean(list []string) []string {
    seen := make(map[string]struct{})
    var out []string

    for _, item := range list {
        item = strings.TrimSpace(item)
        if item == "" {
            continue
        }
        if len(item) < 10 {
            continue
        }
        if _, ok := seen[item]; ok {
            continue
        }
        seen[item] = struct{}{}
        out = append(out, item)
    }

    return out
}
