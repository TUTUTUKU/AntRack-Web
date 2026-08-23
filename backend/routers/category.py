# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from core.response import success, fail
from models.category import Category
from models.material import Material
from schemas.category import CategoryIn

router = APIRouter()


@router.get("/tree")
def tree(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    cats = db.query(Category).order_by(Category.sort.asc(), Category.id.asc()).all()
    rows = db.query(Material.category_id.label("cid"), func.count(Material.id).label("cnt")) \
        .group_by(Material.category_id).all()
    count_map = {r.cid: int(r.cnt) for r in rows}

    level1 = [c for c in cats if c.level == 1]
    tree_data = []
    for c in level1:
        sub_cats = [s for s in cats if s.level == 2 and s.parent_id == c.id]
        level1_total = 0
        children = []
        for s in sub_cats:
            s_cnt = count_map.get(s.id, 0)
            level1_total += s_cnt
            children.append({
                "id": s.id, "name": s.name, "parent_id": s.parent_id,
                "level": s.level, "sort": s.sort, "material_count": s_cnt,
            })
        tree_data.append({
            "id": c.id, "name": c.name, "parent_id": c.parent_id,
            "level": c.level, "sort": c.sort, "children": children,
            "material_count": level1_total,
        })
    return success(tree_data)


@router.get("/list")
def list_all(db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    cats = db.query(Category).order_by(Category.level.asc(), Category.sort.asc(), Category.id.asc()).all()
    return success([
        {"id": c.id, "name": c.name, "parent_id": c.parent_id,
         "level": c.level, "sort": c.sort}
        for c in cats
    ])


@router.post("/save")
def save(data: CategoryIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    if data.level == 2:
        parent = db.query(Category).filter(Category.id == data.parent_id, Category.level == 1).first()
        if not parent:
            return fail("二级分类必须绑定有效的一级分类")
    elif data.level == 1:
        if data.parent_id != 0:
            return fail("一级分类 parent_id 必须为 0")
    else:
        return fail("分类层级仅支持 1 或 2，禁止三级及以上嵌套")

    cat = Category(
        name=data.name.strip(),
        parent_id=data.parent_id if data.level == 2 else 0,
        level=data.level,
        sort=data.sort,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return success({"id": cat.id}, "分类新增成功")


@router.put("/update/{cat_id}")
def update(cat_id: int, data: CategoryIn, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        return fail("分类不存在")
    if cat.level != data.level:
        return fail("不允许变更分类层级")
    if data.level == 2:
        parent = db.query(Category).filter(Category.id == data.parent_id, Category.level == 1).first()
        if not parent:
            return fail("二级分类必须绑定有效的一级分类")
        if data.parent_id == cat.id:
            return fail("不允许将分类挂到自身下")
        cat.parent_id = data.parent_id
    else:
        cat.parent_id = 0
    cat.name = data.name.strip()
    cat.sort = data.sort
    db.commit()
    return success(msg="分类修改成功")


@router.delete("/delete/{cat_id}")
def delete(cat_id: int, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        return fail("分类不存在")
    bind_count = db.query(Material).filter(Material.category_id == cat_id).count()
    if bind_count > 0:
        return fail(f"该分类下已绑定 {bind_count} 个物料，请先迁移物料后再删除")
    if cat.level == 1:
        child_count = db.query(Category).filter(Category.parent_id == cat_id, Category.level == 2).count()
        if child_count > 0:
            return fail(f"该一级分类下还有 {child_count} 个二级子类，请先删除子类")
    db.delete(cat)
    db.commit()
    return success(msg="分类删除成功")
