package telegram

import (
    "encoding/json"
    "fmt"
    "io/ioutil"
    "net/http"
)

type ChatHistoryResponse struct {
    Ok     bool `json:"ok"`
    Result struct {
        Messages []struct {
            Text string `json:"text"`
        } `json:"messages"`
    } `json:"result"`
}

func GetChannelMessages(token, channel string) ([]string, error) {
    url := fmt.Sprintf(
        "https://api.telegram.org/bot%s/getChatHistory?chat_id=@%s&limit=100",
        token, channel,
    )

    resp, err := http.Get(url)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    body, _ := ioutil.ReadAll(resp.Body)

    var data ChatHistoryResponse
    if err := json.Unmarshal(body, &data); err != nil {
        return nil, err
    }

    var out []string
    for _, msg := range data.Result.Messages {
        if msg.Text != "" {
            out = append(out, msg.Text)
        }
    }

    return out, nil
}
