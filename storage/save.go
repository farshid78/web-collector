package storage

import (
    "os"
)

// ذخیره یک فایل ساده
func SaveToFile(filename string, lines []string) error {
    f, err := os.Create(filename)
    if err != nil {
        return err
    }
    defer f.Close()

    for _, line := range lines {
        _, _ = f.WriteString(line + "\n")
    }

    return nil
}

// ذخیره چند فایل (vmess.txt, vless.txt, ...)
func SaveMultiple(groups map[string][]string) error {
    for name, list := range groups {
        filename := name + ".txt"
        if err := SaveToFile(filename, list); err != nil {
            return err
        }
    }
    return nil
}

// ساخت subscription نهایی
func SaveSubscription(filename string, configs []string) error {
    return SaveToFile(filename, configs)
}
