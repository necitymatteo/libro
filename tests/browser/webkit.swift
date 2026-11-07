// Apre una pagina con WebKit, lo stesso motore di Safari, in una finestra fuori schermo.
// Uso: webkit <url> <attesa-secondi> <js-corpo-async oppure @file> <png oppure -> [chiaro|scuro] [larghezza] [altezza]
// ATTESA_MAX: secondi massimi per il codice (default 30).
import Cocoa
import WebKit

let argomenti = CommandLine.arguments
let indirizzo = URL(string: argomenti[1])!
let attesa = Double(argomenti[2])!
var codice = argomenti[3]
if codice.hasPrefix("@") {
    codice = try! String(contentsOfFile: String(codice.dropFirst()), encoding: .utf8)
}
let uscita = argomenti[4]
let tema = argomenti.count > 5 ? argomenti[5] : "chiaro"
let larghezza = argomenti.count > 6 ? Double(argomenti[6])! : 1440
let altezza = argomenti.count > 7 ? Double(argomenti[7])! : 900
let massimo = Double(ProcessInfo.processInfo.environment["ATTESA_MAX"] ?? "30")!

let app = NSApplication.shared
app.setActivationPolicy(.prohibited)
let cornice = NSRect(x: 0, y: 0, width: larghezza, height: altezza)
let vista = WKWebView(frame: cornice, configuration: WKWebViewConfiguration())
let finestra = NSWindow(contentRect: cornice, styleMask: .borderless, backing: .buffered, defer: false)
let aspetto = NSAppearance(named: tema == "scuro" ? .darkAqua : .aqua)
finestra.appearance = aspetto
vista.appearance = aspetto
finestra.contentView = vista
finestra.setFrameOrigin(NSPoint(x: -6000, y: -6000))
finestra.orderFront(nil)
vista.load(URLRequest(url: indirizzo))

DispatchQueue.main.asyncAfter(deadline: .now() + attesa) {
    vista.callAsyncJavaScript(codice, arguments: [:], in: nil, in: .page) { esito in
        switch esito {
        case .success(let valore): print(valore)
        case .failure(let errore): print("ERRORE JS: \(errore)")
        }
        if uscita == "-" { exit(0) }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
            vista.takeSnapshot(with: nil) { immagine, _ in
                guard let immagine, let dati = immagine.tiffRepresentation,
                      let bitmap = NSBitmapImageRep(data: dati),
                      let png = bitmap.representation(using: .png, properties: [:]) else {
                    print("ERRORE: nessuna immagine")
                    exit(1)
                }
                try? png.write(to: URL(fileURLWithPath: uscita))
                exit(0)
            }
        }
    }
}
DispatchQueue.main.asyncAfter(deadline: .now() + attesa + massimo) {
    print("ERRORE: tempo scaduto")
    exit(2)
}
app.run()
