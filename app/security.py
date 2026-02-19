import logging

from flask_appbuilder.security.sqla.manager import SecurityManager

logger = logging.getLogger(__name__)


class DefensiveSecurityManager(SecurityManager):
    """
    Handle stale/invalid user ids in session cookies without crashing.
    """

    def load_user(self, pk):
        try:
            user_id = int(pk)
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid user id in session: %r", pk)
            return None

        user = self.get_user_by_id(user_id)
        if user is None:
            logger.warning("Session user id %s not found. Forcing anonymous user.", user_id)
            return None

        if getattr(user, "is_active", False):
            return user

        return None
