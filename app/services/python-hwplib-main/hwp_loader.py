# services/python-hwplib-main/hwp_loader.py
import jpype
import argparse
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hwp loader')
    parser.add_argument('--hwp_jar_path', type=str, required=True, help='hwplib jar 위치')
    parser.add_argument('--file_path', type=str, required=True, help='hwp 파일 경로')
    parser.add_argument('--output', type=str, required=True, help='본문을 저장할 텍스트파일 경로')
    args = parser.parse_args()

    jpype.startJVM(
        jpype.getDefaultJVMPath(),
        "-Djava.class.path={classpath}".format(classpath=args.hwp_jar_path),
        convertStrings=True,
    )

    HWPReader_class = jpype.JPackage('kr.dogfoot.hwplib.reader')
    TextExtrac_class = jpype.JPackage('kr.dogfoot.hwplib.tool.textextractor')
    HWPReader_ = HWPReader_class.HWPReader
    TextExtractMethod_ = TextExtrac_class.TextExtractMethod
    TextExtractor_ = TextExtrac_class.TextExtractor

    # java.io.File 이용
    javaio = jpype.JPackage('java').io
    file_obj = javaio.File(args.file_path)
    parser_obj = HWPReader_.fromFile(file_obj)

    extract_methods = [
        TextExtractMethod_.InsertControlTextBetweenParagraphText,
        TextExtractMethod_.AppendControlTextAfterParagraphText,
    ]

    best_result = ""
    for method in extract_methods:
        hwpText = TextExtractor_.extract(parser_obj, method)
        if hwpText.strip():
            best_result = hwpText
            break

    jpype.shutdownJVM()

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(best_result)
