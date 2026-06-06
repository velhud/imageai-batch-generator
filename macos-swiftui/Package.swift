// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ImagenNative",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "ImagenNative", targets: ["ImagenNative"])
    ],
    targets: [
        .executableTarget(
            name: "ImagenNative",
            dependencies: [],
            path: "Sources"
        ),
        .testTarget(
            name: "ImagenNativeTests",
            dependencies: ["ImagenNative"],
            path: "Tests"
        )
    ]
)
