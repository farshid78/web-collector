package scraper

import (
    "net/http"
    "time"

    "github.com/PuerkitoBio/goquery"
)

var client = &http.Client{
    Timeout: 30 * time.Second,
}

func FetchDocument(url string) (*goquery.Document, error) {
    resp, err := client.Get(url)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    doc, err := goquery.NewDocumentFromReader(resp.Body)
    if err != nil {
        return nil, err
    }

    return doc, nil
}
