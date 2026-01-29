"""
Python 파일 들여쓰기 자동 수정 스크립트
autopep8을 사용하여 들여쓰기 오류를 자동으로 수정합니다.
"""
import os
import sys
import subprocess


def check_and_install_autopep8():
    """autopep8 패키지가 설치되어 있는지 확인하고, 없으면 설치"""
    try:
        import autopep8
        print("✅ autopep8이 이미 설치되어 있습니다.")
        return True
    except ImportError:
        print("⚠️ autopep8이 설치되어 있지 않습니다.")
        print("📦 autopep8 설치 중...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "autopep8"])
            print("✅ autopep8 설치 완료!")
            return True
        except subprocess.CalledProcessError:
            print("❌ autopep8 설치 실패!")
            return False


def fix_python_file(filepath):
    """개별 Python 파일의 들여쓰기 수정"""
    try:
        # autopep8 명령어 실행 (들여쓰기 및 기본 포맷팅)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "autopep8",
                "--in-place",  # 파일을 직접 수정
                "--aggressive",  # 적극적인 수정
                "--aggressive",  # 더 적극적인 수정
                filepath
            ],
            check=True
        )
        print(f"  ✅ {os.path.basename(filepath)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ {os.path.basename(filepath)} - 오류: {e}")
        return False
    except Exception as e:
        print(f"  ❌ {os.path.basename(filepath)} - 예외: {e}")
        return False


def fix_all_python_files(directory="."):
    """디렉토리 내 모든 Python 파일의 들여쓰기 수정"""
    print("=" * 50)
    print("Python 들여쓰기 자동 수정 프로그램")
    print("=" * 50)
    print()

    # autopep8 설치 확인
    if not check_and_install_autopep8():
        print("\n❌ autopep8을 설치할 수 없어 프로그램을 종료합니다.")
        return

    print(f"\n📁 디렉토리: {os.path.abspath(directory)}")
    print("🔍 Python 파일 검색 중...\n")

    # .py 파일 찾기
    python_files = []
    for root, dirs, files in os.walk(directory):
        # __pycache__ 등 제외
        dirs[:] = [d for d in dirs if d not in [
            '__pycache__', '.git', 'venv', 'env']]

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                python_files.append(filepath)

    if not python_files:
        print("❌ Python 파일을 찾을 수 없습니다.")
        return

    print(f"📝 총 {len(python_files)}개의 Python 파일을 발견했습니다.\n")
    print("🔧 들여쓰기 수정 중...\n")

    # 각 파일 수정
    success_count = 0
    for filepath in python_files:
        if fix_python_file(filepath):
            success_count += 1

    print()
    print("=" * 50)
    print(f"✅ 완료! {success_count}/{len(python_files)}개 파일 수정 성공")
    print("=" * 50)


if __name__ == "__main__":
    try:
        # 현재 디렉토리의 모든 Python 파일 수정
        fix_all_python_files(".")
        input("\n계속하려면 Enter를 누르세요...")
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        input("\n계속하려면 Enter를 누르세요...")
