class InstagramSpiderPaths:
    tag_paths = {"_id": lambda tag: tag.get("id"), "name": lambda tag: tag.get("name")}

    post_paths = {
        "id": lambda post: post.get("id"),
        "text": lambda post: post.get("edge_media_to_caption").get("edges"),
        "url": lambda post: f"https://www.instagram.com/p/{post.get('shortcode')}",
        "edge_media_to_comment": lambda post: post.get("edge_media_to_comment"),
        "taken_at_timestamp": lambda post: post.get("taken_at_timestamp"),
        "dimensions": lambda post: post.get("dimensions"),
        "photo": lambda post: post.get("display_url"),
        "edge_liked_by": lambda post: post.get("edge_liked_by"),
        "edge_media_preview_like": lambda post: post.get("edge_media_preview_like"),
        "owner": lambda post: post.get("owner"),
        "is_video": lambda post: post.get("is_video"),
        "accessibility_caption": lambda post: post.get("accessibility_caption"),
        "photos": lambda post: [post.get("thumbnail_src")],
    }
