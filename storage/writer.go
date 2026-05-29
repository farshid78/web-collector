package storage

import (
    "os"
    "sort"
    "strings"
)

func RemoveDuplicates(items []string) []string {
    seen := make(map[string]bool)
    var result []string
    for _, item := range items {
        if !seen[item] {
            seen[item] = true
            result = append(result, item)
        }
    }
    return result
}

func SaveToFile(filename string, items []string) error {
    if len(items) == 0 {
        return nil
    }

    unique := RemoveDuplicates(items)
    sort.Strings(unique)

    content := strings.Join(unique, "\n")
    return os.WriteFile(filename, []byte(content), 0644)
}
