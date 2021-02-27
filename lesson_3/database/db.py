from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from . import models


class Database:
    def __init__(self, db_url):
        engine = create_engine(db_url)
        models.Base.metadata.create_all(bind=engine)
        self.maker = sessionmaker(bind=engine)

    def _get_or_create(self, session, model, u_field, u_value, **data):
        db_data = session.query(model).filter(u_field == data[u_value]).first()
        if not db_data:
            db_data = model(**data)
        return db_data

    def _get_or_create_comments(self, session, data, post_for_com):
        if data:
            for comment in data:
                writer_comm = self._get_or_create(
                    session,
                    models.Writer,
                    models.Writer.url,
                    "url",
                    name=comment["name"],
                    url=comment["url"],
                )
                session.add(writer_comm)
                comments = models.Comment(
                    text=comment["text"], writer=writer_comm, post=post_for_com
                )
                session.add(comments)

    def create_post(self, data):
        session = self.maker()
        writer = self._get_or_create(
            session, models.Writer, models.Writer.url, "url", **data["writer"],
        )

        post = self._get_or_create(
            session, models.Post, models.Post.url, "url", **data["post_data"], writer=writer
        )
        post.tags.extend(
            map(
                lambda tag_data: self._get_or_create(
                    session, models.Tag, models.Tag.url, "url", **tag_data
                ),
                data["tags"],
            )
        )
        self._get_or_create_comments(session, data["comments"], post)
        session.add(post)
        try:
            session.commit()
        except Exception as exc:
            print(exc)
            session.rollback()
        finally:
            session.close()
