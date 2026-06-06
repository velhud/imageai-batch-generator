import XCTest
@testable import ImagenNative

final class BatchParserTests: XCTestCase {
    func testLines() {
        let parser = BatchParser()
        let res = parser.parse(text: "a\nb", mode: .lines, promptField: "prompt", csvColumn: "0")
        XCTAssertEqual(res.prompts, ["a", "b"])
    }

    func testCSV() {
        let parser = BatchParser()
        let res = parser.parse(text: "prompt,other\nhello,1\nworld,2", mode: .csv, promptField: "prompt", csvColumn: "prompt")
        XCTAssertEqual(res.prompts, ["hello", "world"])
    }
}
