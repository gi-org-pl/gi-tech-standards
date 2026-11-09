# Testing Convention

## BDD (Behavior-Driven Development) - Given When Then

> **#1. Unit and end-to-end tests MUST be written in the Given-When-Then structure.**
>
> We use BDD syntax (Given-When-Then) to write tests in a human-readable format. This makes tests serve as living
> documentation and helps to understand what the application does.

In Vitest, the outer `describe` is the Given, the nested `describe` is the When, and `it` is the Then:

```typescript
describe('<Button />', () => {       // Given
  describe('when clicked', () => {   // When
    it('calls the handler', () => {  // Then
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Click me</Button>);

      fireEvent.click(screen.getByText('Click me'));

      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });
});
```

End-to-end tests are written in Gherkin:

```gherkin
Given a user is on the login page
When they enter valid credentials
Then they should be redirected to the dashboard
```

Read more about BDD:

- [BDD introduction](https://cucumber.io/docs/bdd/)
- [Given-When-Then format](https://martinfowler.com/bliki/GivenWhenThen.html)
