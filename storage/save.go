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
