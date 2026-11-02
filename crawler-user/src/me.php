<?php
/**
 * 현재 로그인 사용자 확인 API
 *
 * 요청: GET /me.php (쿠키 필요)
 * 응답: 로그인 상태 200, 비로그인 401
 */

require __DIR__ . '/session.php';

$session = current_session();

if ($session === null) {
    send_json(401, ['error' => '로그인이 필요합니다.']);
}

send_json(200, [
    'server' => 'crawler-user',
    'username' => $session['username'],
]);
