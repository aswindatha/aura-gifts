from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from app.database import get_db
from app.models import Product, User
from app.schemas import ProductResponse, ProductCreate, ProductUpdate
from app.auth import get_current_user

router = APIRouter(prefix="/api/products", tags=["Products"])

@router.get("", response_model=List[ProductResponse])
async def list_products(
    category: Optional[str] = None,
    exclude_category: Optional[str] = None,
    names: Optional[List[str]] = Query(None),
    ids: Optional[List[int]] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Get products list (paginated, Rule 2.2).
    """
    # Explicit column selection to respect egress limits (Rule 4.1)
    query = select(
        Product.id,
        Product.name,
        Product.description,
        Product.price,
        Product.category,
        Product.badge,
        Product.image_url,
        Product.out_of_stock,
        Product.mrp,
        Product.rating,
        Product.review_count,
        Product.images,
        Product.features,
        Product.specs,
        Product.reviews,
        Product.style_id,
        Product.hex,
        Product.created_at
    )
    
    if category:
        query = query.where(Product.category == category)
    if exclude_category:
        query = query.where(Product.category != exclude_category)
    if names:
        names_list = []
        for n in names:
            if "," in n:
                names_list.extend([x.strip() for x in n.split(",") if x.strip()])
            else:
                names_list.append(n.strip())
        if names_list:
            query = query.where(Product.name.in_(names_list))
    if ids:
        query = query.where(Product.id.in_(ids))
        
    query = query.order_by(Product.id.asc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    products = []
    for row in result.all():
        products.append(
            ProductResponse(
                id=row.id,
                name=row.name,
                description=row.description,
                price=float(row.price),
                category=row.category,
                badge=row.badge,
                image_url=row.image_url,
                out_of_stock=row.out_of_stock,
                mrp=float(row.mrp) if row.mrp is not None else None,
                rating=float(row.rating) if row.rating is not None else None,
                review_count=row.review_count or 0,
                images=row.images or [],
                features=row.features or [],
                specs=row.specs or {},
                reviews=row.reviews or [],
                style_id=row.style_id,
                hex=row.hex,
                created_at=row.created_at
            )
        )
    
    cat_info = f" [category={category}]" if category else " [all categories]"
    print(f"[DB] GET /api/products{cat_info} -> {len(products)} product(s) fetched from database", flush=True)
    return products

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a single product by ID.
    """
    query = select(
        Product.id,
        Product.name,
        Product.description,
        Product.price,
        Product.category,
        Product.badge,
        Product.image_url,
        Product.out_of_stock,
        Product.mrp,
        Product.rating,
        Product.review_count,
        Product.images,
        Product.features,
        Product.specs,
        Product.reviews,
        Product.style_id,
        Product.hex,
        Product.created_at
    ).where(Product.id == product_id)
    
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
        
    return ProductResponse(
        id=row.id,
        name=row.name,
        description=row.description,
        price=float(row.price),
        category=row.category,
        badge=row.badge,
        image_url=row.image_url,
        out_of_stock=row.out_of_stock,
        mrp=float(row.mrp) if row.mrp is not None else None,
        rating=float(row.rating) if row.rating is not None else None,
        review_count=row.review_count or 0,
        images=row.images or [],
        features=row.features or [],
        specs=row.specs or {},
        reviews=row.reviews or [],
        style_id=row.style_id,
        hex=row.hex,
        created_at=row.created_at
    )

@router.post("", response_model=ProductResponse)
async def create_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new product (Admin only).
    """
    if current_user.role != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can add new products"
        )
    
    new_product = Product(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        category=payload.category,
        badge=payload.badge,
        image_url=payload.image_url,
        out_of_stock=False,
        mrp=payload.mrp,
        rating=payload.rating,
        review_count=0,
        images=payload.images,
        features=payload.features,
        specs=payload.specs,
        style_id=payload.style_id,
        hex=payload.hex,
        reviews=[]
    )
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    
    return ProductResponse(
        id=new_product.id,
        name=new_product.name,
        description=new_product.description,
        price=float(new_product.price),
        category=new_product.category,
        badge=new_product.badge,
        image_url=new_product.image_url,
        out_of_stock=new_product.out_of_stock,
        mrp=float(new_product.mrp) if new_product.mrp is not None else None,
        rating=float(new_product.rating) if new_product.rating is not None else None,
        review_count=new_product.review_count,
        images=new_product.images or [],
        features=new_product.features or [],
        specs=new_product.specs or {},
        reviews=new_product.reviews or [],
        style_id=new_product.style_id,
        hex=new_product.hex,
        created_at=new_product.created_at
    )

@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update product attributes (Admin only).
    """
    if current_user.role != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can modify products"
        )
        
    query = select(Product).where(Product.id == product_id)
    result = await db.execute(query)
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
        
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
        
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        price=float(product.price),
        category=product.category,
        badge=product.badge,
        image_url=product.image_url,
        out_of_stock=product.out_of_stock,
        mrp=float(product.mrp) if product.mrp is not None else None,
        rating=float(product.rating) if product.rating is not None else None,
        review_count=product.review_count,
        images=product.images or [],
        features=product.features or [],
        specs=product.specs or {},
        reviews=product.reviews or [],
        style_id=product.style_id,
        hex=product.hex,
        created_at=product.created_at
    )
