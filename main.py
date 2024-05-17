from fastapi import FastAPI, HTTPException, Depends
from fastapi_pagination import Page, LimitOffsetPage, add_pagination, paginate
from fastapi_pagination.limit_offset import LimitOffsetParams
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = "sqlite:///./store.db"  # Altere para a URL do seu banco de dados

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    code = Column(String, unique=True, index=True)
    category = Column(String)
    price = Column(String)

Base.metadata.create_all(bind=engine)

class ProductCreate(BaseModel):
    name: str
    code: str
    category: str
    price: str

class ProductResponse(BaseModel):
    id: int
    name: str
    code: str
    category: str
    price: str

    class Config:
        orm_mode = True

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/products/", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.code == product.code).first()
    if db_product:
        raise HTTPException(status_code=303, detail=f"Product with code {product.code} already exists")
    try:
        db_product = Product(**product.dict())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(status_code=303, detail=f"Product with code {product.code} already exists")

@app.get("/products/", response_model=Page[ProductResponse])
def read_products(db: Session = Depends(get_db), name: str = None, code: str = None):
    query = db.query(Product)
    if name:
        query = query.filter(Product.name == name)
    if code:
        query = query.filter(Product.code == code)
    return paginate(query.all())

@app.get("/products/limit-offset", response_model=LimitOffsetPage[ProductResponse])
def read_products_limit_offset(db: Session = Depends(get_db), params: LimitOffsetParams = Depends()):
    return paginate(db.query(Product).all(), params)

@app.get("/products/{product_id}", response_model=ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

add_pagination(app)
