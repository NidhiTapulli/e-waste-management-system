from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="E-Waste Management System",
    description="Backend API for managing electronic waste",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "EWaste API is running!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/categories")
def get_categories():
    return {
        "categories": [
            "Mobile Phones",
            "Laptops",
            "Computers",
            "Televisions",
            "Batteries",
            "Other Electronics"
        ]
    }


@app.get("/api/items")
def get_items():
    return {
        "items": [
            {
                "id": 1,
                "name": "Old Mobile Phone",
                "category": "Mobile Phones",
                "condition": "Used"
            },
            {
                "id": 2,
                "name": "Old Laptop",
                "category": "Laptops",
                "condition": "Used"
            }
        ]
    }
