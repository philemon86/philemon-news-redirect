import UIKit
import WebKit
import Network
import Foundation

// This app embeds all Bible text and search modules. It only serves content
// from its own read-only app bundle to localhost. It never contacts the site.
@main
final class BibleAppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    private let server = OfflineBibleServer()

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = BibleViewController(server: server)
        window.makeKeyAndVisible()
        self.window = window
        return true
    }
}

final class BibleViewController: UIViewController, WKNavigationDelegate {
    private let server: OfflineBibleServer
    private var webView: WKWebView!

    init(server: OfflineBibleServer) {
        self.server = server
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError("Use init(server:)") }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 250/255, green: 250/255, blue: 250/255, alpha: 1)
        let config = WKWebViewConfiguration()
        config.defaultWebpagePreferences.allowsContentJavaScript = true
        config.websiteDataStore = .default()
        let webView = WKWebView(frame: .zero, configuration: config)
        self.webView = webView
        webView.navigationDelegate = self
        webView.isOpaque = false
        webView.backgroundColor = view.backgroundColor
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(webView)

        // Fixed site header must never overlap the notch or status bar.
        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            webView.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor),
            webView.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor)
        ])

        server.start { [weak self] result in
            DispatchQueue.main.async {
                guard let self = self else { return }
                switch result {
                case .success(let url):
                    self.webView.load(URLRequest(url: url))
                case .failure(let error):
                    let label = UILabel()
                    label.text = "離線聖經資料啟動失敗。\n\(error.localizedDescription)"
                    label.numberOfLines = 0
                    label.textAlignment = .center
                    label.translatesAutoresizingMaskIntoConstraints = false
                    self.view.addSubview(label)
                    NSLayoutConstraint.activate([
                        label.centerXAnchor.constraint(equalTo: self.view.centerXAnchor),
                        label.centerYAnchor.constraint(equalTo: self.view.centerYAnchor),
                        label.leadingAnchor.constraint(greaterThanOrEqualTo: self.view.leadingAnchor, constant: 20),
                        label.trailingAnchor.constraint(lessThanOrEqualTo: self.view.trailingAnchor, constant: -20)
                    ])
                }
            }
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if let url = action.request.url,
           url.scheme == "http", url.host == "127.0.0.1", url.port == 58942 {
            decisionHandler(.allow)
        } else {
            // Prevent online pages or nonlocal resources from opening here.
            decisionHandler(.cancel)
        }
    }
}

/// A small read-only localhost HTTP server makes ES modules, Workers and fetch()
/// work in WKWebView without internet or PWA cache. Bind to loopback ONLY.
final class OfflineBibleServer {
    private let queue = DispatchQueue(label: "tw.com.philemon.bible.offline", qos: .userInitiated)
    private var listener: NWListener?
    private let port = NWEndpoint.Port(rawValue: 58942)!
    private var didComplete = false

    func start(completion: @escaping (Result<URL, Error>) -> Void) {
        let params = NWParameters.tcp
        params.requiredLocalEndpoint = .hostPort(host: NWEndpoint.Host("127.0.0.1"), port: port)
        do {
            let listener = try NWListener(using: params, on: port)
            self.listener = listener
            listener.stateUpdateHandler = { [weak self] state in
                guard let self = self, !self.didComplete else { return }
                switch state {
                case .ready:
                    self.didComplete = true
                    completion(.success(URL(string: "http://127.0.0.1:58942/")!))
                case .failed(let error):
                    self.didComplete = true
                    completion(.failure(error))
                default: break
                }
            }
            listener.newConnectionHandler = { [weak self] connection in
                self?.respond(to: connection)
            }
            listener.start(queue: queue)
        } catch {
            completion(.failure(error))
        }
    }

    private func respond(to connection: NWConnection) {
        connection.start(queue: queue)
        connection.receive(minimumIncompleteLength: 1, maximumLength: 16384) {
            [weak self] data, _, _, error in
            guard let self = self, error == nil, let data = data,
                  let request = String(data: data, encoding: .utf8),
                  let firstLine = request.components(separatedBy: "\r\n").first else {
                connection.cancel()
                return
            }
            let parts = firstLine.split(separator: " ")
            guard parts.count >= 2, parts[0] == "GET" || parts[0] == "HEAD" else {
                self.send(connection, status: "405 Method Not Allowed", body: Data(), mime: "text/plain")
                return
            }
            let raw = String(parts[1]).components(separatedBy: "?")[0]
            let decoded = raw.removingPercentEncoding ?? raw
            let relative = decoded == "/" ? "index.html" : String(decoded.dropFirst())
            guard decoded.hasPrefix("/"), !relative.isEmpty,
                  !relative.split(separator: "/").contains(".."),
                  !relative.contains("\\"),
                  !relative.contains("\0") else {
                self.send(connection, status: "403 Forbidden", body: Data(), mime: "text/plain")
                return
            }
            let root = Bundle.main.bundleURL.appendingPathComponent("web", isDirectory: true)
            let fileURL = root.appendingPathComponent(relative).standardizedFileURL
            guard fileURL.path.hasPrefix(root.standardizedFileURL.path + "/"),
                  let body = try? Data(contentsOf: fileURL), !body.isEmpty else {
                self.send(connection, status: "404 Not Found", body: Data(), mime: "text/plain")
                return
            }
            let ext = fileURL.pathExtension.lowercased()
            let mime: String
            switch ext {
            case "html": mime = "text/html"
            case "js": mime = "text/javascript"
            case "css": mime = "text/css"
            case "json": mime = "application/json"
            case "csv": mime = "text/csv"
            case "svg": mime = "image/svg+xml"
            case "png": mime = "image/png"
            case "jpg", "jpeg": mime = "image/jpeg"
            case "woff": mime = "font/woff"
            case "woff2": mime = "font/woff2"
            default: mime = "application/octet-stream"
            }
            self.send(connection, status: "200 OK",
                      body: parts[0] == "HEAD" ? Data() : body,
                      mime: mime, contentLength: body.count)
        }
    }

    private func send(_ connection: NWConnection, status: String, body: Data,
                      mime: String, contentLength: Int? = nil) {
        let headers = [
            "HTTP/1.1 \(status)",
            "Content-Type: \(mime); charset=utf-8",
            "Content-Length: \(contentLength ?? body.count)",
            "Cache-Control: no-store",
            "X-Content-Type-Options: nosniff",
            "Connection: close",
            "",
            ""
        ].joined(separator: "\r\n")
        var packet = Data(headers.utf8)
        packet.append(body)
        connection.send(content: packet, completion: .contentProcessed { _ in
            connection.cancel()
        })
    }
}
