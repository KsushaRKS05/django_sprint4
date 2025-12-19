# blog/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.db.models import Count
from .forms import CustomUserCreationForm, PostForm, CommentForm
from .forms import UserUpdateForm
from .models import Post, Category, Comment


def index(request):
    post_list = Post.objects.select_related(
        'category', 'location', 'author'
    ).filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now()
    ).annotate(comment_count=Count('comments')).order_by('-pub_date')

    paginator = Paginator(post_list, settings.POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'post_list': page_obj,
    }
    return render(request, 'blog/index.html', context)


def post_detail(request, id):
    post = get_object_or_404(
        Post.objects.select_related('category', 'location', 'author'),
        id=id
    )

    can_view = (
        post.is_published and post.category.is_published and post.pub_date
        <= timezone.now()
    )
    is_author = request.user == post.author

    if not can_view and not is_author:
        return render(request, 'pages/404.html', status=404)

    comments = post.comments.all().select_related('author')

    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect('blog:post_detail', id=id)
    else:
        form = CommentForm()

    context = {
        'post': post,
        'comments': comments,
        'form': form,
        'can_view': can_view,
        'is_author': is_author,
    }
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    post_list = Post.objects.select_related(
        'category', 'location', 'author'
    ).filter(
        category=category,
        is_published=True,
        pub_date__lte=timezone.now()
    ).annotate(comment_count=Count('comments')).order_by('-pub_date')

    paginator = Paginator(post_list, settings.POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

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
        ).select_related('category', 'location').annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')
    else:
        post_list = Post.objects.filter(
            author=user,
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        ).select_related('category', 'location').annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')

    paginator = Paginator(post_list, settings.POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile': user,
        'profile_user': user,
        'page_obj': page_obj,
        'posts': page_obj,
        'is_owner': is_owner,
    }
    return render(request, 'blog/profile.html', context)


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('blog:profile', username=user.username)
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/registration_form.html',
                  {'form': form})


@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ваш профиль успешно обновлен!')
            return redirect('blog:profile', username=request.user.username)
    else:
        form = UserUpdateForm(instance=request.user)

    context = {
        'form': form,
        'profile': request.user,
    }
    return render(request, 'blog/user.html', context)


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user

            if post.pub_date > timezone.now():
                post.is_published = False

            post.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        form = PostForm()

    return render(request, 'blog/create.html', {'form': form})


@login_required
def post_edit(request, id):
    post = get_object_or_404(Post, id=id)

    if post.author != request.user:
        return redirect('blog:post_detail', id=id)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            edited_post = form.save(commit=False)
            if edited_post.pub_date > timezone.now():
                edited_post.is_published = False
            else:
                edited_post.is_published = True
            edited_post.save()
            return redirect('blog:post_detail', id=id)
    else:
        form = PostForm(instance=post)

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

    if request.method == 'POST':
        form = CommentForm(request.POST)
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

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', id=id)
    else:
        form = CommentForm(instance=comment)

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


@login_required
def edit_profile_redirect(request):
    return redirect('blog:edit_profile_with_username',
                    username=request.user.username)
