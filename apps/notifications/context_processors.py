from .models import Notification

def unread_notifications(request):
    if request.user.is_authenticated:
        unread = Notification.objects.filter(user=request.user, is_read=False)
        return {
            'unread_notifications': unread,
            'unread_notifications_count': unread.count()
        }
    return {
        'unread_notifications': [],
        'unread_notifications_count': 0
    }
