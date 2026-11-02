<?php
// 로그인 API
// 요청: POST username, password
// 응답: 200 성공, 400 입력 누락, 401 계정 불일치, 405 잘못된 메서드, 429 실패 횟수 초과

require __DIR__ . '/db.php';
require __DIR__ . '/session.php';

const LOGIN_FAIL_LIMIT = 10;    // 허용 실패 횟수
const LOGIN_FAIL_SECONDS = 600; // 실패 횟수 유지 시간(초)

// 없는 아이디도 같은 시간이 걸리게 하는 비교용 해시
const DUMMY_PASSWORD_HASH = '$2y$10$lOFD49tN3uOfpkekOqRS5.pTK1C9L0ULbP9qrIVIJzHhHQveEbXaS';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    send_json(405, ['error' => 'POST 요청만 허용합니다.']);
}

$username = $_POST['username'] ?? '';
$password = $_POST['password'] ?? '';

if (!is_string($username) || !is_string($password) || $username === '' || $password === '') {
    send_json(400, ['error' => '아이디와 비밀번호를 입력하세요.']);
}

// 사용자별 실패 횟수 키
$redis = redis_client();
$fail_key = 'login_fail:' . hash('sha256', strtolower($username));

// 비밀번호 대입 공격 차단
if ((int) $redis->get($fail_key) >= LOGIN_FAIL_LIMIT) {
    send_json(429, ['error' => '로그인 실패가 너무 많습니다. 10분 후 다시 시도하세요.']);
}

// 회원 조회
$select_user = db_connection()->prepare(
    'SELECT id, username, password_hash FROM users WHERE username = ?'
);
$select_user->execute([$username]);
$user = $select_user->fetch();

// 계정 존재 여부와 상관없이 비밀번호 검증
$password_hash = $user['password_hash'] ?? DUMMY_PASSWORD_HASH;

if ($user === false || !password_verify($password, $password_hash)) {
    // 첫 실패에만 만료 시간 설정
    if ($redis->incr($fail_key) === 1) {
        $redis->expire($fail_key, LOGIN_FAIL_SECONDS);
    }

    // 아이디 존재 여부 노출 방지
    send_json(401, ['error' => '아이디 또는 비밀번호가 올바르지 않습니다.']);
}

// 성공 시 실패 횟수 삭제
$redis->del($fail_key);

$user_id = (int) $user['id'];
create_session($user_id, $user['username']);
send_json(200, ['user_id' => $user_id, 'username' => $user['username']]);