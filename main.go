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

    // فقط کانفیگ‌های واقعی
    pattern := `(vmess|vless|trojan|ss)://[^\s]+`

    for _, src := range sources {
        fmt.Println("در حال اسکرپ:", src.URL)

        doc, err := scraper.FetchDocument(src.URL)
        if err != nil {
            fmt.Println("   خطا در دریافت صفحه:", err)
            continue
        }

        // فقط متن پیام‌های تلگرام (نه کل HTML)
        text := extractText(doc)

        matches := parser.ExtractByPattern(text, pattern)
        if len(matches) == 0 {
            fmt.Println("   هیچ کانفیگی پیدا نشد.")
            continue
        }

        fmt.Printf("   کانفیگ‌های پیدا شده: %d\n", len(matches))
        allConfigs = append(allConfigs, matches...)
    }

    // حذف تکراری‌ها + حذف لینک‌های خراب
    cleaned := uniqueAndClean(allConfigs)
    fmt.Printf("\nتعداد نهایی کانفیگ‌های یکتا: %d\n", len(cleaned))

    if err := storage.SaveToFile("results.txt", cleaned); err != nil {
        fmt.Println("خطا در ذخیره نتایج:", err)
    } else {
        fmt.Println("نتایج در فایل results.txt ذخیره شد")
    }
}

// فقط متن پیام‌های واقعی تلگرام را استخراج می‌کند
func extractText(doc *goquery.Document) string {
    var out string

    doc.Find(".tgme_widget_message_text").Each(func(i int, s *goquery.Selection) {
        out += s.Text() + "\n"
    })

    doc.Find(".tgme_widget_message_text a").Each(func(i int, s *goquery.Selection) {
        href, ok := s.Attr("href")
        if ok {
            out += href + "\n"
        }
    })

    doc.Find("a.tgme_widget_message_bubble").Each(func(i int, s *goquery.Selection) {
        href, ok := s.Attr("href")
        if ok {
            out += href + "\n"
        }
    })

    return out
}


// حذف لینک‌های خراب + حذف تکراری‌ها
func uniqueAndClean(list []string) []string {
    seen := make(map[string]struct{})
    var out []string

    for _, item := range list {
        item = strings.TrimSpace(item)
        if item == "" {
            continue
        }

        // حذف لینک‌های خراب
        if strings.Contains(item, "catch(") ||
            strings.Contains(item, "function") ||
            strings.Contains(item, "}}") ||
            strings.Contains(item, "');") ||
            strings.Contains(item, "اینترنت") { // مخصوص مورد تو
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
