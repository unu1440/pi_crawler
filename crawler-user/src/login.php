<?php
/**
 * 테스트 로그인 API
 *
 * 세션 공유를 검증하기 위한 임시 구현이다.
 * 회원 DB를 붙이기 전까지 환경변수의 테스트 계정 하나만 사용한다.
 *
 * 요청: POST /login.php (username, password)
 * 응답: 성공 200, 입력 누락 400, 계정 불일치 401
 */

require __DIR__ . '/session.php';

// 비밀번호가 주소에 남지 않도록 POST 요청만 허용
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    send_json(405, ['error' => 'POST 요청만 허용합니다.']);
}

$username = $_POST['username'] ?? '';
$password = $_POST['password'] ?? '';

if ($username === '' || $password === '') {
    send_json(400, ['error' => '아이디와 비밀번호를 입력하세요.']);
}

$test_username = getenv('TEST_USERNAME');
$test_password = getenv('TEST_PASSWORD');

// 환경변수가 없으면 빈 비밀번호로 로그인되는 일이 없도록 먼저 차단
if (!$test_username || !$test_password) {
    send_json(500, ['error' => '테스트 계정이 설정되지 않았습니다.']);
}

// hash_equals: 비교 시간 차이로 값을 추측하는 공격을 막음
$is_valid = hash_equals($test_username, $username)
    && hash_equals($test_password, $password);

if (!$is_valid) {
    send_json(401, ['error' => '아이디 또는 비밀번호가 올바르지 않습니다.']);
}

create_session($username);
send_json(200, ['username' => $username]);
