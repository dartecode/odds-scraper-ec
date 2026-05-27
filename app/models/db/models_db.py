from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime
from sqlalchemy.sql import func

from app.config.database import Base


class CasaApuesta(Base):
    __tablename__ = "casa_apuesta"

    id = Column(BigInteger, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    url = Column(Text)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())

    proveedor_id = Column(BigInteger, nullable=True)
    integracion = Column(String(100), nullable=True)