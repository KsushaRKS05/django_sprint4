# blog/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.db.models import Count
from django.core.paginator import Paginator

from .models import Post, Category, Comment
from .forms import CustomUserCreationForm, PostForm, CommentForm
from .forms import UserUpdateForm


def get_published_posts(queryset=None):
    if queryset is None:
        queryset = Post.objects.all()

    return queryset.filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now()
    )


def add_comment_count(queryset):
    return queryset.annotate(comment_count=Count('comments'))


def get_paginated_page(request, queryset):
    paginator = Paginator(queryset, settings.POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def index(request):
    post_list = get_published_posts().select_related(
        'category', 'location', 'author'
    )
    post_list = add_comment_count(post_list).order_by('-pub_date')

    page_obj = get_paginated_page(request, post_list)

    context = {
        'page_obj': page_obj,
        'post_list': page_obj,
    }
    return render(request, 'blog/index.html', context)


def post_detail(request, id):
    """Детальная страница поста"""
    post = get_object_or_404(
        Post.objects.select_related('category', 'location', 'author'),
        id=id
    )

    is_author = request.user == post.author

    if not is_author:
        post = get_object_or_404(
            get_published_posts(),
            id=id
        )

    comments = post.comments.all().select_related('author')

    form = CommentForm(request.POST or None)
    if request.method == 'POST' and request.user.is_authenticated:
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect('blog:post_detail', id=id)

    context = {
        'post': post,
        'comments': comments,
        'form': form,
        'is_author': is_author,
    }
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    queryset = category.post_set.all()
    post_list = get_published_posts(queryset).select_related(
        'category', 'location', 'author'
    )
    post_list = add_comment_count(post_list).order_by('-pub_date')

    page_obj = get_paginated_page(request, post_list)

    context = {
        'category': category,
        'page_obj': page_obj,
        'post_list': page_obj,
    }
    return render(request, 'blog/category.html', context)


def profile(request, username):
    user = get_object_or_404(User, username=username)

    is_owner = request.user == user

    if is_owner:
        post_list = Post.objects.filter(
            author=user
        ).select_related('category', 'location')
    else:
        post_list = get_published_posts().filter(
            author=user
        ).select_related('category', 'location')

    post_list = add_comment_count(post_list).order_by('-pub_date')

    page_obj = get_paginated_page(request, post_list)

    context = {
        'profile': user,
        'profile_user': user,
        'page_obj': page_obj,
        'posts': page_obj,
        'is_owner': is_owner,
    }
    return render(request, 'blog/profile.html', context)


def register(request):
    form = CustomUserCreationForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('blog:profile', username=user.username)

    return render(request, 'registration/registration_form.html',
                  {'form': form})


@login_required
def edit_profile(request):
    form = UserUpdateForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Ваш профиль успешно обновлен!')
        return redirect('blog:profile', username=request.user.username)

    context = {
        'form': form,
        'profile': request.user,
    }
    return render(request, 'blog/user.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)

    return render(request, 'blog/create.html', {'form': form})


@login_required
def post_edit(request, id):
    post = get_object_or_404(Post, id=id)

    if post.author != request.user:
        return redirect('blog:post_detail', id=id)

    form = PostForm(request.POST or None, request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', id=id)

    context = {
        'form': form,
        'post': post,
        'is_edit': True,
    }
    return render(request, 'blog/create.html', context)


@login_required
def post_delete(request, id):
    post = get_object_or_404(Post, id=id)

    if post.author != request.user:
        return redirect('blog:post_detail', id=id)

    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)

    context = {'post': post}
    return render(request, 'blog/detail.html', context)


@login_required
def add_comment(request, id):
    post = get_object_or_404(Post, id=id)

    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()

    return redirect('blog:post_detail', id=id)


@login_required
def edit_comment(request, id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, post_id=id)

    if comment.author != request.user:
        return redirect('blog:post_detail', id=id)

    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', id=id)

    context = {
        'form': form,
        'comment': comment,
        'post': comment.post,
    }
    return render(request, 'blog/comment.html', context)


@login_required
def delete_comment(request, id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, post_id=id)

    if comment.author != request.user:
        return redirect('blog:post_detail', id=id)

    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', id=id)

    context = {
        'comment': comment,
        'post': comment.post,
    }
    return render(request, 'blog/comment.html', context)
