from sqlalchemy.orm import Session

from app.models.quiz import Quiz, QuizAttempt


def create_quiz(db: Session, user_id: int, chat_id: int, num_questions: int, questions: list[dict]) -> Quiz:
    """Persist a generated quiz (including correct answers) for later grading."""
    quiz = Quiz(
        user_id=user_id,
        chat_id=chat_id,
        num_questions=num_questions,
        questions=questions,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def get_quiz(db: Session, quiz_id: int, user_id: int) -> Quiz | None:
    """Fetch a quiz, scoped to its owning user."""
    return db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == user_id).first()


def create_quiz_attempt(
    db: Session,
    quiz_id: int,
    user_id: int,
    answers: list[int],
    score: int,
    total_questions: int,
) -> QuizAttempt:
    """Persist a graded quiz attempt."""
    attempt = QuizAttempt(
        quiz_id=quiz_id,
        user_id=user_id,
        answers=answers,
        score=score,
        total_questions=total_questions,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def list_quiz_history(db: Session, user_id: int, chat_id: int) -> list[Quiz]:
    """List quizzes generated for a chat, most recent first."""
    return (
        db.query(Quiz)
        .filter(Quiz.user_id == user_id, Quiz.chat_id == chat_id)
        .order_by(Quiz.created_at.desc())
        .all()
    )


def get_latest_attempt(db: Session, quiz_id: int, user_id: int) -> QuizAttempt | None:
    """Fetch the most recent attempt for a quiz, if any."""
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.submitted_at.desc())
        .first()
    )
