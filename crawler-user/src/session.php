<?php
// Redis 세션 공통 함수
// FastAPI도 읽을 수 있도록 PHP 기본 세션 대신 JSON으로 저장
// 키: session:<세션 ID>
// 값: {"user_id": 1, "username": "lee", "created_at": 1790000000}

const SESSION_COOKIE = 'CRAWLERSESSID'; // 쿠키 이름
const SESSION_TTL = 3600;               // 세션 유지 시간(초)

// Redis 연결
function redis_client(): Redis
{
    $redis = new Redis();
    $redis->connect(getenv('REDIS_HOST') ?: 'crawler-redis', 6379, 2.0);
    return $redis;
}

// 쿠키의 세션 ID 조회, 형식이 틀리면 null
function session_id_from_cookie(): ?string
{
    $session_id = $_COOKIE[SESSION_COOKIE] ?? null;

    if (!is_string($session_id) || preg_match('/\A[0-9a-f]{64}\z/', $session_id) !== 1) {
        return null;
    }

    return $session_id;
}

// 쿠키 전송
function send_session_cookie(string $session_id, int $expires_at): void
{
    setcookie(SESSION_COOKIE, $session_id, [
        'expires' => $expires_at,
        'path' => '/',
        'httponly' => true,   // JavaScript 접근 차단
        'samesite' => 'Lax',  // 외부 사이트 POST 요청에 쿠키 제외
    ]);
}

// 로그인 성공 시 세션 생성
function create_session(int $user_id, string $username): void
{
    $session_id = bin2hex(random_bytes(32)); // 추측 불가능한 세션 ID

    $session_json = json_encode([
        'user_id' => $user_id,
        'username' => $username,
        'created_at' => time(),
    ], JSON_UNESCAPED_UNICODE);

    // 만료 시간과 함께 저장
    redis_client()->setex("session:{$session_id}", SESSION_TTL, $session_json);
    send_session_cookie($session_id, time() + SESSION_TTL);
}

// 현재 세션 조회, 없으면 null
function current_session(): ?array
{
    $session_id = session_id_from_cookie();
    if ($session_id === null) {
        return null;
    }

    $session_json = redis_client()->get("session:{$session_id}");
    if ($session_json === false) {
        return null;
    }

    return json_decode($session_json, true);
}

// 세션과 쿠키 삭제
function destroy_session(): void
{
    $session_id = session_id_from_cookie();
    if ($session_id !== null) {
        redis_client()->del("session:{$session_id}");
    }

    send_session_cookie('', time() - SESSION_TTL);
}

// JSON 응답 후 종료
function send_json(int $status, array $body): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($body, JSON_UNESCAPED_UNICODE);
    exit;
}