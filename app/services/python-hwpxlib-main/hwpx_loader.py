import jpype
import argparse
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hwpx loader')
    parser.add_argument('--hwpx_jar_path', type=str, required=True, help='hwpxlib jar 위치')
    parser.add_argument('--file_path', type=str, required=True, help='hwpx 파일 경로')
    parser.add_argument('--output', type=str, required=True, help='본문을 저장할 텍스트파일 경로')
    args = parser.parse_args()

    jpype.startJVM(
        jpype.getDefaultJVMPath(),
        "-Djava.class.path={classpath}".format(classpath=args.hwpx_jar_path),
        convertStrings=True,
    )

    HWPXReader_class = jpype.JPackage('kr.dogfoot.hwpxlib.reader')
    TextExtrac_class = jpype.JPackage('kr.dogfoot.hwpxlib.tool.textextractor')
    HWPXReader_ = HWPXReader_class.HWPXReader
    TextExtractMethod_ = TextExtrac_class.TextExtractMethod
    TextExtractor_ = TextExtrac_class.TextExtractor
    TextMarks_ = TextExtrac_class.TextMarks   # 추가

    # Java의 java.io.File 클래스를 import
    javaio = jpype.JPackage('java').io
    file_obj = javaio.File(args.file_path)
    parser_obj = HWPXReader_.fromFile(file_obj)

    extract_methods = [
        TextExtractMethod_.InsertControlTextBetweenParagraphText,
        TextExtractMethod_.AppendControlTextAfterParagraphText,
    ]

    best_result = ""
    for method in extract_methods:
        hwpxText = TextExtractor_.extract(
            parser_obj,
            method,
            True,
            TextMarks_()
        )
        if hwpxText.strip():
            best_result = hwpxText
            break

    jpype.shutdownJVM()

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(best_result)
