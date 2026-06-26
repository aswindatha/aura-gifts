from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.database import get_db
from app.models import Cart, CartItem, Product, User
from app.schemas import CartResponse, CartItemResponse, CartItemCreate, CartItemUpdate
from app.auth import get_current_user

router = APIRouter(prefix="/api/cart", tags=["Shopping Cart"])

async def get_or_create_cart(user_id: UUID, db: AsyncSession) -> Cart:
    # Check if cart exists
    query = select(Cart).where(Cart.user_id == user_id)
    result = await db.execute(query)
    cart = result.scalars().first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
    return cart

async def build_cart_response(cart_id: UUID, db: AsyncSession) -> CartResponse:
    # Retrieve all items in the cart with products
    query = (
        select(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .where(CartItem.cart_id == cart_id)
        .order_by(CartItem.created_at.asc())
    )
    result = await db.execute(query)
    
    items_response = []
    subtotal = 0.0
    
    for cart_item, product in result.all():
        item_total = float(product.price) * cart_item.quantity
        subtotal += item_total
        items_response.append(
            CartItemResponse(
                id=cart_item.id,
                product_id=product.id,
                name=product.name,
                price=float(product.price),
                quantity=cart_item.quantity,
                unit_price=float(cart_item.unit_price),
                image_url=product.image_url,
                category=product.category
            )
        )
        
    tax = round(subtotal * 0.08, 2)
    total = round(subtotal + tax, 2)
    
    return CartResponse(
        items=items_response,
        subtotal=round(subtotal, 2),
        tax=tax,
        total=total
    )

@router.get("", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the current user's shopping cart.
    """
    cart = await get_or_create_cart(current_user.id, db)
    return await build_cart_response(cart.id, db)

@router.post("/items", response_model=CartResponse)
async def add_cart_item(
    payload: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a product to the cart or increase its quantity.
    """
    cart = await get_or_create_cart(current_user.id, db)
    
    # Check if product exists
    prod_query = select(Product).where(Product.id == payload.product_id)
    prod_result = await db.execute(prod_query)
    product = prod_result.scalars().first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
        
    # Check if item already in cart
    item_query = select(CartItem).where(
        CartItem.cart_id == cart.id,
        CartItem.product_id == payload.product_id
    )
    item_result = await db.execute(item_query)
    cart_item = item_result.scalars().first()
    
    if cart_item:
        cart_item.quantity += payload.quantity
        db.add(cart_item)
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            unit_price=product.price
        )
        db.add(cart_item)
        
    await db.commit()
    return await build_cart_response(cart.id, db)

@router.patch("/items/{item_id}", response_model=CartResponse)
async def update_cart_item(
    item_id: UUID,
    payload: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the quantity of an item in the cart.
    """
    cart = await get_or_create_cart(current_user.id, db)
    
    query = select(CartItem).where(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    )
    result = await db.execute(query)
    cart_item = result.scalars().first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
        
    if payload.quantity <= 0:
        await db.delete(cart_item)
    else:
        cart_item.quantity = payload.quantity
        db.add(cart_item)
        
    await db.commit()
    return await build_cart_response(cart.id, db)

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_cart_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove an item from the cart.
    """
    cart = await get_or_create_cart(current_user.id, db)
    
    query = select(CartItem).where(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    )
    result = await db.execute(query)
    cart_item = result.scalars().first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
        
    await db.delete(cart_item)
    await db.commit()
    return
