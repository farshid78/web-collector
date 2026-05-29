package input

import (
    "os"

    "github.com/jszwec/csvutil"
    "web-collector/models"
)

func ReadSourcesFromCSV(path string) ([]models.Source, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, err
    }

    var sources []models.Source
    if err := csvutil.Unmarshal(data, &sources); err != nil {
        return nil, err
    }

    return sources, nil
}
