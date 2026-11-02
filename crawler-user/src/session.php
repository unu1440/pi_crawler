<?php
/**
 * Redis 세션 공통 함수
 *
 * PHP 기본 세션은 PHP 전용 형식으로 저장되어 FastAPI에서 읽기 어렵다.
 * 그래서 세션을 JSON으로 직접 저장해 두 서버가 같은 데이터를 읽게 한다.
 *
 * 저장 형식
 *   키: session:<세션 ID>
 *   값: {"username": "...", "created_at": 유닉스 시각}
 */

// 브라우저 쿠키 이름 (crawler-api와 같은 값을 사용해야 함)
const SESSION_COOKIE = 'CRAWLERSESSID';

// 세션 유지 시간(초): 1시간
const SESSION_TTL = 3600;

/**
 * Redis 연결을 만들어 돌려준다.
 * 접속 주소는 컨테이너 이름이며 환경변수로 바꿀 수 있다.
 */
function redis_client(): Redis
{
    $redis = new Redis();
    $redis->connect(getenv('REDIS_HOST') ?: 'crawler-redis', 6379, 2.0);
    return $redis;
}

/**
 * 쿠키의 세션 ID가 형식에 맞는지 확인한다.
 * 임의의 문자열이 Redis 키로 쓰이지 않도록 64자리 16진수만 허용한다.
 */
function is_valid_session_id(string $session_id): bool
{
    return preg_match('/^[0-9a-f]{64}$/', $session_id) === 1;
}

/**
 * 로그인 성공 시 세션을 만들고 브라우저에 쿠키를 보낸다.
 */
function create_session(string $username): void
{
    // 추측할 수 없도록 암호학적으로 안전한 난수로 세션 ID 생성
    $session_id = bin2hex(random_bytes(32));

    $data = json_encode([
        'username' => $username,
        'created_at' => time(),
    ], JSON_UNESCAPED_UNICODE);

    // SETEX: 만료 시간과 함께 저장해 오래된 세션이 자동으로 지워지게 함
    redis_client()->setex("session:{$session_id}", SESSION_TTL, $data);

    // HttpOnly: 자바스크립트에서 쿠키를 읽지 못하게 막음
    // SameSite=Lax: 다른 사이트에서 보낸 POST 요청에 쿠키가 붙지 않게 함
    setcookie(SESSION_COOKIE, $session_id, [
        'expires' => time() + SESSION_TTL,
        'path' => '/',
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
}

/**
 * 현재 요청의 세션을 읽는다. 로그인 상태가 아니면 null을 돌려준다.
 */
function current_session(): ?array
{
    $session_id = $_COOKIE[SESSION_COOKIE] ?? '';
    if (!is_valid_session_id($session_id)) {
        return null;
    }

    $data = redis_client()->get("session:{$session_id}");
    if ($data === false) {
        return null;
    }

    return json_decode($data, true);
}

/**
 * Redis의 세션과 브라우저 쿠키를 모두 지운다.
 */
function destroy_session(): void
{
    $session_id = $_COOKIE[SESSION_COOKIE] ?? '';
    if (is_valid_session_id($session_id)) {
        redis_client()->del("session:{$session_id}");
    }

    setcookie(SESSION_COOKIE, '', [
        'expires' => time() - 3600,
        'path' => '/',
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
}

/**
 * JSON 응답을 보내고 실행을 끝낸다.
 */
function send_json(int $status, array $body): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($body, JSON_UNESCAPED_UNICODE);
    exit;
}
