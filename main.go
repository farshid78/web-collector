package main

import (
    "fmt"

    "github.com/PuerkitoBio/goquery"
    "web-collector/input"
    "web-collector/parser"
    "web-collector/scraper"
    "web-collector/storage"
)

func main() {
    fmt.Println("شروع برنامه جمع‌آوری داده...\n")

    sources, err := input.ReadSourcesFromCSV("sources.csv")
    if err != nil {
        fmt.Println("خطا در خواندن فایل CSV:", err)
        return
    }

    fmt.Printf("تعداد منبع‌ها: %d\n\n", len(sources))

    var allMatches []string

    // یک الگوی نمونه: همه لینک‌های http/https
    pattern := `https?://[^\s]+`

    for _, src := range sources {
        fmt.Println("در حال اسکرپ:", src.URL)

        doc, err := scraper.FetchDocument(src.URL)
        if err != nil {
            fmt.Println("   خطا در دریافت صفحه:", err)
            continue
        }

        text := extractText(doc)
        matches := parser.ExtractByPattern(text, pattern)
        allMatches = append(allMatches, matches...)
    }

    if err := storage.SaveToFile("results.txt", allMatches); err != nil {
        fmt.Println("خطا در ذخیره نتایج:", err)
    } else {
        fmt.Println("نتایج در فایل results.txt ذخیره شد")
    }
}

func extractText(doc *goquery.Document) string {
    return doc.Text()
}
