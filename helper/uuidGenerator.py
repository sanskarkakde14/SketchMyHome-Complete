import base64
import uuid
def generate_short_uuid():
    full_uuid = uuid.uuid4().bytes
    return base64.urlsafe_b64encode(full_uuid)[:8].decode('ascii')