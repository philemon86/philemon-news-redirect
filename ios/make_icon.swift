import AppKit

let size: CGFloat = 1024
let image = NSImage(size: NSSize(width: size, height: size))
image.lockFocus()
let rect = NSRect(x: 0, y: 0, width: size, height: size)
NSColor(calibratedRed: 18/255, green: 103/255, blue: 214/255, alpha: 1).setFill()
NSBezierPath(roundedRect: rect, xRadius: 200, yRadius: 200).fill()
let arrow = "↗"
let font = NSFont.systemFont(ofSize: 570, weight: .regular)
let attributes: [NSAttributedString.Key: Any] = [
    .font: font,
    .foregroundColor: NSColor.white
]
let textSize = arrow.size(withAttributes: attributes)
arrow.draw(at: NSPoint(x: (size-textSize.width)/2,
                       y: (size-textSize.height)/2 + 80), withAttributes: attributes)
image.unlockFocus()
guard let tiff = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let png = bitmap.representation(using: .png, properties: [:]) else {
    fatalError("icon render failed")
}
try png.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
