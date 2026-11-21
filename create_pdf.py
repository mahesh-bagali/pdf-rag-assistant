
from reportlab.pdfgen import canvas

pdf = canvas.Canvas("data/sample.pdf")
pdf.setTitle("Introduction to Python")

lines = [
    "Introduction to Python Programming",
    "Python is a popular programming language.",
    "It is used in web development and automation.",
    "Python supports variables, functions, loops, and classes.",
    "FastAPI is a Python framework used to build APIs.",
    "RAG stands for Retrieval-Augmented Generation.",
    "RAG retrieves relevant information before generating an answer."
]

y = 750

for line in lines:
    pdf.drawString(70, y, line)
    y -= 35

pdf.save()

print("Valid PDF created successfully!")