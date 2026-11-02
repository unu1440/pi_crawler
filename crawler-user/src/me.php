<?php
// 현재 로그인 사용자 확인 API
// 응답: 200 로그인 상태, 401 비로그인

require __DIR__ . '/session.php';

$session = current_session();

if ($session === null) {
    send_json(401, ['error' => '로그인이 필요합니다.']);
}

// server: 응답한 서버 구분용
send_json(200, [
    'server' => 'crawler-user',
    'user_id' => $session['user_id'],
    'username' => $session['username'],
]);