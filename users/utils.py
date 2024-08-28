def get_avatar_upload_path(instance, filename):
    base_path = "images/avatars"
    return f"{base_path}/{instance.user.id}/{filename}"
