<?php
// 회원가입 API
// 요청: POST username, password
// 응답: 201 성공, 400 형식 오류, 405 잘못된 메서드, 409 아이디 중복

require __DIR__ . '/db.php';
require __DIR__ . '/session.php';

// 비밀번호가 주소에 남지 않도록 POST만 허용
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    send_json(405, ['error' => 'POST 요청만 허용합니다.']);
}

$username = $_POST['username'] ?? '';
$password = $_POST['password'] ?? '';

// 아이디: 영문, 숫자, 밑줄 3~30자
if (!is_string($username) || preg_match('/\A[A-Za-z0-9_]{3,30}\z/', $username) !== 1) {
    send_json(400, ['error' => '아이디는 영문, 숫자, 밑줄 3~30자로 입력하세요.']);
}

// 비밀번호: bcrypt 제한에 맞춰 8~72바이트
if (!is_string($password) || strlen($password) < 8 || strlen($password) > 72) {
    send_json(400, ['error' => '비밀번호는 8~72바이트로 입력하세요.']);
}

try {
    // SQL 주입 방지를 위한 값 분리
    $insert_user = db_connection()->prepare(
        'INSERT INTO users (username, password_hash) VALUES (?, ?)'
    );
    $insert_user->execute([$username, password_hash($password, PASSWORD_DEFAULT)]);
} catch (PDOException $error) {
    // 23000: UNIQUE 제약 위반
    if ($error->getCode() === '23000') {
        send_json(409, ['error' => '이미 사용 중인 아이디입니다.']);
    }
    throw $error;
}

$user_id = (int) db_connection()->lastInsertId();
create_session($user_id, $username);
send_json(201, ['user_id' => $user_id, 'username' => $username]);