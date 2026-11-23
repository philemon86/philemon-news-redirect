# 咻咻查聖經 — iPhone 離線開發版本

This iOS app embeds the original Soonsoon Bible search interface and all 66 Bible-book data files. It uses an in-app HTTP server bound exclusively to 127.0.0.1; WKWebView loads this local server so JavaScript ES Modules, fetch() and Web Workers can work. The app doesn't need the public philemon.com.tw domain once installed.

## 編譯

Requires macOS and Xcode with an iPhoneOS SDK:

```sh
python3 android/mirror.py
bash ios/build-unsigned-ipa.sh output
```

The output IPA is an **unsigned developer-test package**, not directly installable from WeChat or Files on an ordinary iPhone.

## 寄送中國大陸使用者測試（正常簽章途徑）

1. 把 `SoonsoonBible-iOS-UNSIGNED.ipa` 用微信「檔案」傳送給對方。
2. 對方需要一台 Windows 或 Mac 電腦、Apple 帳號與相容簽署安裝工具（例如 Sideloadly），為自己的裝置簽署並安裝。
3. 免費 Apple 帳號的測試描述檔通常 7 天到期，需重新簽署。部分 iOS 版本及簽章方式需要開啟開發者模式。
4. 安裝後切換飛航模式測試「約3:16」、簡體「约3:16」、關鍵字「信心」，複製經文、退出再開。
5. 較穩定、更多人使用的安裝方式需使用 Apple 正式允許的測試或發布途徑，並確認當地規範。

## 限制

- 直接點擊微信收到的 IPA 不會繞過 Apple 簽章。
- 尚未在中國大陸實體 iPhone 上實測。
- 不建議以企業內部簽章、共享憑證、越獄或利用漏洞作為公開發行方式。
- 離線內容保留 66 卷聖經及本機搜尋，不提供線上排行與流量統計。
