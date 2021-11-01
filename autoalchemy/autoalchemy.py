"""Main module."""

from __future__ import annotations

from functools import wraps
from typing import Union

from sqlalchemy.orm import MANYTOMANY, MANYTOONE, ONETOMANY
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.orm.relationships import RelationshipProperty
from sqlalchemy.sql.base import ColumnCollection
from sqlalchemy.util._collections import ImmutableProperties

from ._handler import AutoInitializer
from .config import AutoInitConfig


def auto_init(exclude: Union[set, list] = None, config: AutoInitConfig = None):  # sourcery no-metrics
    """Wraps the `__init__` method of a class to automatically set the common
    attributes.

    Args:
        exclude (Union[set, list], optional): [description]. Defaults to None.
    """

    exclude = exclude or set()
    exclude.add("id")

    def decorator(init):
        @wraps(init)
        def wrapper(self: DeclarativeMeta, *args, **kwargs):  # sourcery no-metrics
            """
            Custom initializer that allows nested children initialization.
            Only keys that are present as instance's class attributes are allowed.
            These could be, for example, any mapped columns or relationships.

            Code inspired from GitHub.
            Ref: https://github.com/tiangolo/fastapi/issues/2194
            """
            cls = self.__class__

            # Accesses the underlying table from the parent class of `self` to determine the primary key name
            # 'id' in most cases
            alchemy_mapper: Mapper = self.__mapper__

            model_columns: ColumnCollection = alchemy_mapper.columns
            relationships: ImmutableProperties = alchemy_mapper.relationships

            session = kwargs.get("session", None)

            initializer = AutoInitializer(session, config)

            if session is None:
                raise ValueError("Session is required to initialize the model with `auto_init`")

            for key, val in kwargs.items():
                if key in exclude:
                    continue

                if not hasattr(cls, key):
                    continue
                    # raise TypeError(f"Invalid keyword argument: {key}")

                if key in model_columns:
                    setattr(self, key, val)
                    continue

                if key in relationships:
                    prop: RelationshipProperty = relationships[key]

                    # Identifies the type of relationship (ONETOMANY, MANYTOONE, many-to-one, many-to-many)
                    relation_dir = prop.direction

                    # Identifies the parent class of the related object.
                    relation_cls: DeclarativeMeta = prop.mapper.entity

                    # Identifies if the relationship was declared with use_list=True
                    use_list: bool = prop.uselist

                    get_attr = initializer.lookup_attr(relation_cls)

                    if relation_dir == ONETOMANY and use_list:
                        instances = initializer.handle_one_to_many_list(get_attr, relation_cls, val)
                        setattr(self, key, instances)

                    elif relation_dir == ONETOMANY:
                        instance = relation_cls(**val)
                        setattr(self, key, instance)

                    elif relation_dir == MANYTOONE and not use_list:
                        if isinstance(val, dict):
                            val = val.get(get_attr)

                            if val is None:
                                raise ValueError(f"Expected 'id' to be provided for {key}")

                        if isinstance(val, (str, int)):
                            instance = session.query(relation_cls).filter_by(**{get_attr: val}).one_or_none()
                            setattr(self, key, instance)

                    elif relation_dir == MANYTOMANY:
                        instances = initializer.handle_many_to_many(get_attr, relation_cls, val)
                        setattr(self, key, instances)

            return init(self, *args, **kwargs)

        return wrapper

    return decorator
