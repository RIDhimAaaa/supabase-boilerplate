"""Initial commit

Revision ID: e6389d678a7d
Revises: 
Create Date: 2025-07-03 18:18:01.555050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e6389d678a7d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('learn-table')
    op.add_column('profiles', sa.Column('first_name', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('last_name', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('avatar_url', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('phone', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('bio', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.add_column('profiles', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.alter_column('profiles', 'email',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=False,
               existing_server_default=sa.text("''::text"))
    op.drop_constraint(op.f('profiles_email_key'), 'profiles', type_='unique')
    op.drop_constraint(op.f('profiles_username_key'), 'profiles', type_='unique')
    op.create_index(op.f('ix_profiles_email'), 'profiles', ['email'], unique=True)
    op.drop_constraint(op.f('profiles_id_fkey'), 'profiles', type_='foreignkey')
    op.drop_column('profiles', 'username')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('profiles', sa.Column('username', sa.TEXT(), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('profiles_id_fkey'), 'profiles', 'users', ['id'], ['id'], referent_schema='auth', ondelete='CASCADE')
    op.drop_index(op.f('ix_profiles_email'), table_name='profiles')
    op.create_unique_constraint(op.f('profiles_username_key'), 'profiles', ['username'], postgresql_nulls_not_distinct=False)
    op.create_unique_constraint(op.f('profiles_email_key'), 'profiles', ['email'], postgresql_nulls_not_distinct=False)
    op.alter_column('profiles', 'email',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=False,
               existing_server_default=sa.text("''::text"))
    op.drop_column('profiles', 'updated_at')
    op.drop_column('profiles', 'is_active')
    op.drop_column('profiles', 'bio')
    op.drop_column('profiles', 'phone')
    op.drop_column('profiles', 'avatar_url')
    op.drop_column('profiles', 'last_name')
    op.drop_column('profiles', 'first_name')
    op.create_table('learn-table',
    sa.Column('id', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('first_name', sa.TEXT(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('learn-table_pkey'))
    )
    # ### end Alembic commands ###
