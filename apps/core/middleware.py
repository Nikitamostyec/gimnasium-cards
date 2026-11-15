class SecurityHeadersMiddleware:
    """Добавляет строгие заголовки Content-Security-Policy и Referrer-Policy."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://jsdelivr.net https://googleapis.com; "
            "font-src 'self' https://jsdelivr.net https://gstatic.com; "
            "img-src 'self' data:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        return response
