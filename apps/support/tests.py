from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import Student
from apps.support.models import SupportAgent, SupportTicket, ChatRoom, Message

User = get_user_model()

class SupportSystemTestCase(TestCase):
    def setUp(self):
        # 1. Create a student user and profile
        self.student_user = User.objects.create_user(
            username="test_student",
            email="student@test.com",
            password="password123",
            role="student"
        )
        self.student = Student.objects.create(user=self.student_user, phone="1234567890")

        # 2. Create an agent user and support agent profile
        self.agent_user = User.objects.create_user(
            username="test_agent",
            email="agent@test.com",
            password="password123",
            role="instructor"
        )
        self.agent = SupportAgent.objects.create(
            user=self.agent_user,
            department="technical",
            status="online"
        )

    def test_support_agent_creation(self):
        """Test that a SupportAgent profile is set up correctly."""
        self.assertEqual(self.agent.user.username, "test_agent")
        self.assertEqual(self.agent.department, "technical")
        self.assertEqual(self.agent.status, "online")
        self.assertIn("test_agent", str(self.agent))

    def test_support_ticket_creation_and_uuid(self):
        """Test ticket creation and automatic prefix ID generation."""
        ticket = SupportTicket.objects.create(
            student=self.student,
            category="technical",
            subject="Cannot connect to WebSockets",
            description="WebSocket connection fails on /ws/ support path.",
            priority="high",
            status="open"
        )
        
        # Verify automatic ticket ID generation starts with TKT- prefix
        self.assertTrue(ticket.ticket_id.startswith("TKT-"))
        self.assertEqual(len(ticket.ticket_id), 10)  # TKT- + 6 characters
        self.assertEqual(ticket.status, "open")
        self.assertEqual(ticket.priority, "high")
        self.assertIn(ticket.subject, str(ticket))

    def test_chat_room_and_message_delivery(self):
        """Test that a ChatRoom is created and messages can be sent/delivered."""
        room = ChatRoom.objects.create(
            student=self.student,
            support_agent=self.agent
        )
        
        # Verify relationships
        self.assertEqual(room.student, self.student)
        self.assertEqual(room.support_agent, self.agent)
        self.assertIn("test_student", str(room))

        # Send a message
        msg = Message.objects.create(
            chatroom=room,
            sender=self.student_user,
            message="Hello, I need assistance."
        )

        # Verify message property defaults
        self.assertEqual(msg.message, "Hello, I need assistance.")
        self.assertFalse(msg.is_read)
        self.assertEqual(msg.sender, self.student_user)
        self.assertIn("test_student", str(msg))
