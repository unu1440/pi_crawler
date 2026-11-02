<?php
/**
 * 로그아웃 API
 *
 * Redis의 세션을 지우므로 crawler-api에서도 바로 로그아웃 상태가 된다.
 *
 * 요청: POST /logout.php (쿠키 필요)
 * 응답: 200
 */

require __DIR__ . '/session.php';

// 링크 클릭만으로 로그아웃되지 않도록 POST 요청만 허용
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    send_json(405, ['error' => 'POST 요청만 허용합니다.']);
}

destroy_session();
send_json(200, ['message' => '로그아웃되었습니다.']);
