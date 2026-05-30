package main

import (
    "bufio"
    "fmt"
    "os"
    "strings"
)

func main() {
    inFile := "../configs.txt"
    outFile := "../results.txt"

    f, err := os.Open(inFile)
    if err != nil {
        fmt.Println("خطا در باز کردن configs.txt:", err)
        return
    }
    defer f.Close()

    seen := make(map[string]bool)
    var lines []string

    scanner := bufio.NewScanner(f)
    for scanner.Scan() {
        line := strings.TrimSpace(scanner.Text())
        if line == "" {
            continue
        }
        if !seen[line] {
            seen[line] = true
            lines = append(lines, line)
        }
    }

    out, err := os.Create(outFile)
    if err != nil {
        fmt.Println("خطا در ساخت results.txt:", err)
        return
    }
    defer out.Close()

    for _, l := range lines {
        out.WriteString(l + "\n")
    }

    fmt.Println("تمام شد. تعداد نهایی:", len(lines))
}
