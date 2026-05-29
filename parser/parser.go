package parser

import (
    "regexp"
    "strings"
)

func ExtractByPattern(text, pattern string) []string {
    re := regexp.MustCompile(pattern)
    matches := re.FindAllString(text, -1)

    var result []string
    for _, m := range matches {
        m = strings.TrimSpace(m)
        if m != "" {
            result = append(result, m)
        }
    }
    return result
}
