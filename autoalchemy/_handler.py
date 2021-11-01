from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy.orm.decl_api import DeclarativeMeta

from .config import AutoInitConfig


class AutoInitializer:
    """Auto initializer for the AutoAlchemy class"""

    def __init__(self, session: Session, config: AutoInitConfig = None) -> None:
        self.session: Session = session
        self.config: AutoInitConfig = config or AutoInitConfig()

    def lookup_attr(self, relation_cls: DeclarativeMeta) -> str:
        """Returns the primary key attribute of the related class as a string.

        Args:
            relation_cls (DeclarativeMeta): The SQLAlchemy class to get the primary_key from

        Returns:
            Any: [description]
        """

        try:
            cfg: AutoInitConfig = relation_cls.Config
            get_attr = cfg.get_attr
            if get_attr is None:
                get_attr = relation_cls.__table__.primary_key.columns.keys()[0]
        except Exception:
            get_attr = "id"
        return get_attr

    def handle_many_to_many(self, get_attr, relation_cls, all_elements: list[dict]):
        """
        Proxy call to `handle_one_to_many_list` for many-to-many relationships. Because
        functionally, they do the same
        """
        return self.handle_one_to_many_list(get_attr, relation_cls, all_elements)

    def handle_one_to_many_list(self, get_attr, relation_cls, all_elements: list[dict]):
        elems_to_create: list[dict] = []
        updated_elems: list[dict] = []

        for elem in all_elements:
            elem_id = elem.get(get_attr, None)

            existing_elem = self.session.query(relation_cls).filter_by(**{get_attr: elem_id}).one_or_none()

            if existing_elem is None:
                elems_to_create.append(elem)

            else:
                for key, value in elem.items():
                    setattr(existing_elem, key, value)

                updated_elems.append(existing_elem)

        new_elems = []
        for elem in elems_to_create:
            try:
                del elem["slug"]
            except KeyError:
                pass

            new_elems.append(relation_cls(**elem))

        return new_elems + updated_elems
