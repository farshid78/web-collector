package storage

import (
    "os"
)

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

func SaveMultiple(groups map[string][]string) error {
    for name, list := range groups {
        filename := name + ".txt"
        if err := SaveToFile(filename, list); err != nil {
            return err
        }
    }
    return nil
}

func SaveSubscription(filename string, configs []string) error {
    return SaveToFile(filename, configs)
}
