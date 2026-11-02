<?php
// 로그아웃 API
// 응답: 200 성공, 405 잘못된 메서드

require __DIR__ . '/session.php';

// 링크 클릭만으로 로그아웃되는 것 방지
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    send_json(405, ['error' => 'POST 요청만 허용합니다.']);
}

destroy_session();
send_json(200, ['message' => '로그아웃되었습니다.']);