"""
并发提交测试：模拟 100 个学生同时提交代码
"""
import requests
import concurrent.futures
import time
import os

BASE_URL = 'http://127.0.0.1:8000'
CONCURRENT_WORKERS = 20

TEST_CODE = '''
def main():
    print("Hello World")
    for i in range(10):
        print(f"Number: {i}")

if __name__ == "__main__":
    main()
'''

def get_token(username, password='test1234'):
    try:
        res = requests.post(f'{BASE_URL}/api/auth/login/', json={
            'username': username,
            'password': password
        }, timeout=10)
        if res.status_code == 200:
            return res.json().get('access')
    except Exception as e:
        print(f'Login failed for {username}: {e}')
    return None

def submit_code(student_id, assignment_id, token):
    try:
        import zipfile
        import io

        # 创建一个包含多个文件的 ZIP 包
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('src/main.py', TEST_CODE)
            zf.writestr('src/utils.py', 'def helper():\n    return 42\n')
            zf.writestr('src/config.py', 'CONFIG = {"debug": True}\n')
        zip_buffer.seek(0)

        test_file = f'test_{student_id}.zip'
        with open(test_file, 'wb') as f:
            f.write(zip_buffer.read())

        with open(test_file, 'rb') as f:
            res = requests.post(
                f'{BASE_URL}/api/auth/student/submissions/',
                headers={'Authorization': f'Bearer {token}'},
                files={'file': (test_file, f, 'application/zip')},
                data={'assignment': assignment_id},
                timeout=60
            )

        os.remove(test_file)

        if res.status_code in [200, 201]:
            return {'student': student_id, 'status': 'success'}
        else:
            return {'student': student_id, 'status': 'failed', 'code': res.status_code}
    except Exception as e:
        return {'student': student_id, 'status': 'error', 'error': str(e)}

def run_concurrent_test():
    assignment_id = input('Enter assignment ID: ').strip()
    if not assignment_id.isdigit():
        print('Invalid assignment ID')
        return

    print(f'\n=== Concurrent Test: 100 students, {CONCURRENT_WORKERS} workers ===\n')

    print('Step 1: Getting tokens...')
    tokens = {}
    for i in range(1, 101):
        username = f'test_student_{i:03d}'
        token = get_token(username)
        if token:
            tokens[username] = token
    print(f'Got {len(tokens)} tokens\n')

    if len(tokens) < 2:
        print('Not enough valid tokens.')
        return

    print(f'Step 2: Submitting {len(tokens)} files concurrently...')
    results = []
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
        futures = {
            executor.submit(submit_code, username, assignment_id, token): username
            for username, token in tokens.items()
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            icon = '+' if result['status'] == 'success' else 'x'
            print(f'  {icon} {result["student"]}: {result["status"]}')

    elapsed = time.time() - start_time
    success = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - success

    print(f'\n=== Results ===')
    print(f'Total: {len(results)} | Success: {success} | Failed: {failed}')
    print(f'Time: {elapsed:.2f}s | Avg: {elapsed/len(results):.2f}s')

if __name__ == '__main__':
    run_concurrent_test()