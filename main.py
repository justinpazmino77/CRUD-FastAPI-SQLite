from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from contextlib import asynccontextmanager

# =================================================================
# 1. CONFIGURACIÓN DE LA BASE DE DATOS SQLITE
# =================================================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./sistema_academico.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# =================================================================
# 2. CREACIÓN DE LAS 3 TABLAS EN SQL (Modelos SQLAlchemy)
# =================================================================
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    correo = Column(String, unique=True, index=True)


class Asignatura(Base):
    __tablename__ = "asignaturas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)


class Paralelo(Base):
    __tablename__ = "paralelos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)


# =================================================================
# 3. ESQUEMAS PYDANTIC (Validan los datos que entran y salen)
# =================================================================
class UsuarioBase(BaseModel):
    nombre: str
    correo: str


class UsuarioCreate(UsuarioBase):
    pass


class UsuarioResponse(UsuarioBase):
    id: int

    class Config:
        from_attributes = True


# =================================================================
# 4. INYECCIÓN DE DATOS INICIALES (20 Usuarios, 6 Asig, 3 Paralelos)
# =================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas físicamente en el archivo .db
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Si la tabla paralelos está vacía, insertamos los 3 registros
        if db.query(Paralelo).count() == 0:
            db.add_all([
                Paralelo(nombre="Paralelo 01"),
                Paralelo(nombre="Paralelo 02"),
                Paralelo(nombre="Paralelo 03")
            ])

        # Si la tabla asignaturas está vacía, insertamos 6 registros
        if db.query(Asignatura).count() == 0:
            db.add_all([
                Asignatura(nombre="Fundamentos de Programación"),
                Asignatura(nombre="Lógica, Estructura y Algoritmos"),
                Asignatura(nombre="Cálculo Diferencial"),
                Asignatura(nombre="Física"),
                Asignatura(nombre="Álgebra Lineal"),
                Asignatura(nombre="Ciencia de Datos")
            ])

        # Si la tabla usuarios está vacía, generamos 20 registros
        if db.query(Usuario).count() == 0:
            usuarios_iniciales = [
                Usuario(nombre=f"Estudiante {i}", correo=f"estudiante{i}@uce.edu.ec")
                for i in range(1, 21)
            ]
            db.add_all(usuarios_iniciales)

        db.commit()
    finally:
        db.close()
    yield


# Inicializamos FastAPI
app = FastAPI(lifespan=lifespan)


# Dependencia para abrir y cerrar la base de datos en cada petición
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =================================================================
# 5. EL CRUD (Listar, Agregar, Editar, Eliminar) PARA USUARIOS
# =================================================================

# READ (Listar todos los registros)
@app.get("/usuarios/", response_model=list[UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).all()


# CREATE (Agregar un registro nuevo)
@app.post("/usuarios/", response_model=UsuarioResponse)
def agregar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    db_usuario = db.query(Usuario).filter(Usuario.correo == usuario.correo).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    nuevo_usuario = Usuario(nombre=usuario.nombre, correo=usuario.correo)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


# UPDATE (Editar un registro existente)
@app.put("/usuarios/{usuario_id}", response_model=UsuarioResponse)
def editar_usuario(usuario_id: int, usuario_actualizado: UsuarioCreate, db: Session = Depends(get_db)):
    usuario_db = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario_db.nombre = usuario_actualizado.nombre
    usuario_db.correo = usuario_actualizado.correo
    db.commit()
    db.refresh(usuario_db)
    return usuario_db


# DELETE (Eliminar un registro)
@app.delete("/usuarios/{usuario_id}")
def eliminar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario_db = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.delete(usuario_db)
    db.commit()
    return {"mensaje": f"Usuario {usuario_id} eliminado exitosamente"}